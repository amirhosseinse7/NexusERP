from django.db import models
from django.utils import timezone
from django.db import transaction

from apps.core.models import Material, Partner, SystemSequence, TenantAwareModel
from apps.inventory.models import StockQuant, StockMove, StorageLocation, StockPicking, StockPickingType


from simple_history.models import HistoricalRecords

def get_picking_type(code):
    """
    Helper to safely get picking types or create defaults to prevent crashes.
    """
    pt, created = StockPickingType.objects.get_or_create(code=code, defaults={'name': f"Default {code}"})
    

    if not pt.default_source_location or not pt.default_dest_location:
        if code == 'IN':
            loc, _ = StorageLocation.objects.get_or_create(location_id='PARTNER', defaults={'name':'Vendor', 'type':'supplier'})
            pt.default_source_location = loc
            dest_loc, _ = StorageLocation.objects.get_or_create(location_id='WH-MAIN', defaults={'name':'Main Warehouse', 'type':'internal'})
            pt.default_dest_location = dest_loc
            
        elif code == 'OUT':
            src_loc, _ = StorageLocation.objects.get_or_create(location_id='WH-MAIN', defaults={'name':'Main Warehouse', 'type':'internal'})
            pt.default_source_location = src_loc
            loc, _ = StorageLocation.objects.get_or_create(location_id='CUSTOMER', defaults={'name':'Customer', 'type':'customer'})
            pt.default_dest_location = loc
            
        elif code == 'RET':
            src_loc, _ = StorageLocation.objects.get_or_create(location_id='CUSTOMER', defaults={'name':'Customer', 'type':'customer'})
            pt.default_source_location = src_loc
            dest_loc, _ = StorageLocation.objects.get_or_create(location_id='WH-MAIN', defaults={'name':'Main Warehouse', 'type':'internal'})
            pt.default_dest_location = dest_loc

        pt.save()
    return pt

class Vehicle(TenantAwareModel):
    vehicle_id = models.CharField(max_length=50, primary_key=True)
    max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.vehicle_id

class PurchaseOrder(TenantAwareModel):
    po_id = models.CharField(max_length=50, primary_key=True, blank=True)
    supplier = models.ForeignKey(Partner, on_delete=models.CASCADE, limit_choices_to={'is_supplier': True})
    date_order = models.DateTimeField(default=timezone.now)
    state = models.CharField(
        max_length=20, 
        choices=[('draft', 'Draft'), ('sent', 'Sent'), ('partial', 'Partial'), ('received', 'Done')], 
        default='draft'
    )


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.po_id:
            self.po_id = SystemSequence.get_next('purchase.order', 'PO-', 4, "Purchase Orders")
        super().save(*args, **kwargs)

    def confirm_order(self):
        if self.state != 'draft': return
        
        with transaction.atomic():
            self.state = 'sent'
            self.save()
            
            pick_type = get_picking_type('IN')

            picking = StockPicking.objects.create(
                picking_type=pick_type,
                origin=self.po_id,
                state='assigned'
            )

            for line in self.lines.all():
                StockMove.objects.create(
                    move_id=f"MV-{self.po_id}-{line.id}",
                    material=line.material,
                    qty=line.qty_requested,
                    location_source=pick_type.default_source_location,
                    location_dest=pick_type.default_dest_location,
                    state='draft',
                    reference=self.po_id,
                    picking=picking
                )
                
                quant, _ = StockQuant.objects.get_or_create(material=line.material, location=pick_type.default_dest_location)
                quant.quantity_incoming += line.qty_requested
                quant.save()

    def receive_gap(self):
        if self.state in ['draft', 'received']: return

        with transaction.atomic():
            picking = StockPicking.objects.filter(origin=self.po_id, state='assigned').first()
            if picking:
                picking.validate_picking()
                
            self.state = 'received'
            self.save()
            
            for line in self.lines.all():
                line.qty_received = line.qty_requested
                line.save()

    def create_bill(self):
        from apps.finance.models import Invoice, InvoiceLine
        

        if Invoice.objects.filter(source_document=self.po_id).exists():
            return
            
        with transaction.atomic():
            bill = Invoice.objects.create(
                type='in_invoice',
                partner=self.supplier,
                source_document=self.po_id,
                state='draft'
            )
            for line in self.lines.all():
                if line.qty_received > 0:
                    InvoiceLine.objects.create(
                        invoice=bill,
                        description=line.material.name,
                        quantity=line.qty_received,
                        unit_price=line.price_unit
                    )
            bill.post() 

class PurchaseOrderLine(TenantAwareModel):
    order = models.ForeignKey(PurchaseOrder, related_name='lines', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    qty_requested = models.DecimalField(max_digits=12, decimal_places=2)
    qty_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_unit = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def progress(self):
        return (self.qty_received / self.qty_requested) * 100 if self.qty_requested > 0 else 0

class SalesOrder(TenantAwareModel):
    so_id = models.CharField(max_length=50, primary_key=True, blank=True)
    customer = models.ForeignKey(Partner, on_delete=models.CASCADE, limit_choices_to={'is_customer': True})
    date_order = models.DateTimeField(default=timezone.now)
    delivery_mode = models.CharField(max_length=20, choices=[('normal', 'Normal'), ('green', 'Green Mode')])
    state = models.CharField(
        max_length=20, 
        choices=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('partial', 'Partial'), ('shipped', 'Done'), ('returned', 'Returned')], 
        default='draft'
    )


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.so_id:
            self.so_id = SystemSequence.get_next('sales.order', 'SO-', 4, "Sales Orders")
        super().save(*args, **kwargs)

    def update_prices(self):
        if not self.customer.pricelist: return
        for line in self.lines.all():
            new_price = self.customer.pricelist.get_price(line.material)
            line.price_unit = new_price 
            line.save()

    def confirm_order(self):
        if self.state != 'draft': return

        with transaction.atomic():
            pick_type = get_picking_type('OUT')
            target_loc = pick_type.default_source_location
            
            for line in self.lines.all():

                quant = StockQuant.objects.select_for_update().filter(
                    material=line.material, location=target_loc
                ).first()
                

                if not quant:
                    quant = StockQuant.objects.create(material=line.material, location=target_loc)

                if quant.quantity_available < line.qty_requested:
                    raise ValueError(f"Not enough stock for {line.material.sku}. Available: {quant.quantity_available}")
                
                quant.quantity_reserved += line.qty_requested
                quant.save()


            picking = StockPicking.objects.create(
                picking_type=pick_type,
                origin=self.so_id,
                state='assigned'
            )

            for line in self.lines.all():
                StockMove.objects.create(
                    move_id=f"MV-{self.so_id}-{line.id}",
                    material=line.material,
                    qty=line.qty_requested,
                    location_source=pick_type.default_source_location,
                    location_dest=pick_type.default_dest_location,
                    state='draft',
                    reference=self.so_id,
                    picking=picking
                )

            self.state = 'confirmed'
            self.save()

    def ship_gap(self):
        if self.state not in ['confirmed', 'partial']: return

        with transaction.atomic():
            picking = StockPicking.objects.filter(origin=self.so_id, state='assigned').first()
            if picking:
                picking.validate_picking()
            
            self.state = 'shipped'
            self.save()
            
            for line in self.lines.all():
                line.qty_delivered = line.qty_requested
                line.save()

    def return_order(self):
        if self.state != 'shipped': return

        with transaction.atomic():
            pick_type = get_picking_type('RET')
            
            picking = StockPicking.objects.create(
                picking_type=pick_type,
                origin=f"RMA-{self.so_id}",
                state='assigned'
            )

            for line in self.lines.all():
                StockMove.objects.create(
                    move_id=f"MV-RET-{self.so_id}-{line.id}",
                    material=line.material,
                    qty=line.qty_delivered, 
                    location_source=pick_type.default_source_location,
                    location_dest=pick_type.default_dest_location,
                    state='draft',
                    reference=f"RMA-{self.so_id}",
                    picking=picking
                )
            
            self.state = 'returned'
            self.save()

    def create_invoice(self):
        from apps.finance.models import Invoice, InvoiceLine
        
        if Invoice.objects.filter(source_document=self.so_id).exists():
            return
            
        with transaction.atomic():
            invoice = Invoice.objects.create(
                type='out_invoice',
                partner=self.customer,
                source_document=self.so_id,
                state='draft'
            )
            for line in self.lines.all():
                if line.qty_delivered > 0:
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        description=line.material.name,
                        quantity=line.qty_delivered,
                        unit_price=line.price_unit
                    )
            invoice.post()

class SalesOrderLine(TenantAwareModel):
    order = models.ForeignKey(SalesOrder, related_name='lines', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    qty_requested = models.DecimalField(max_digits=12, decimal_places=2)
    qty_delivered = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)