from django.db import models
from django.utils import timezone
from django.db import transaction

from apps.core.models import Material, Partner, TenantAwareModel


from simple_history.models import HistoricalRecords

class StorageLocation(TenantAwareModel):
    TYPE_CHOICES = [
        ('internal', 'Internal Warehouse'),
        ('customer', 'Customer Location'),
        ('supplier', 'Vendor Location'),
        ('loss', 'Inventory Loss'),
    ]
    
    location_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='internal')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

class StockLot(TenantAwareModel):
    lot_id = models.CharField(max_length=50, primary_key=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    expiry_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"Lot {self.lot_id}"

class StockQuant(TenantAwareModel):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE)
    lot = models.ForeignKey(StockLot, on_delete=models.SET_NULL, null=True, blank=True)
    
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_incoming = models.DecimalField(max_digits=12, decimal_places=2, default=0)


    history = HistoricalRecords()

    class Meta:
        unique_together = ('material', 'location', 'lot')

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved
    
    @property
    def quantity_forecasted(self):
        return self.quantity_available + self.quantity_incoming
        
    @property
    def stock_value(self):
        return self.quantity_on_hand * self.material.cost_price

    def __str__(self):
        return f"{self.material.sku} @ {self.location.location_id}"

    def evaluate_reorder_rules(self):
        """ Checks if this material needs to be ordered, and generates a PO if true. """
        if not getattr(self.material, 'auto_reorder', False):
            return
        
        if self.quantity_forecasted >= self.material.min_stock_level:
            return
            
        from apps.logistics.models import PurchaseOrderLine, PurchaseOrder
        if PurchaseOrderLine.objects.filter(material=self.material, order__state='draft').exists():
            return
            
        qty_to_order = getattr(self.material, 'custom_reorder_qty', 0)
        if not qty_to_order:
            qty_to_order = self.material.max_stock_level - self.quantity_forecasted
            
        if qty_to_order <= 0: return
            
        supplier = getattr(self.material, 'preferred_supplier', None)
        if not supplier:
            supplier = Partner.objects.filter(is_supplier=True).first()
            if not supplier: return
                
        po = PurchaseOrder.objects.filter(supplier=supplier, state='draft').first()
        if not po:
            po = PurchaseOrder.objects.create(supplier=supplier, state='draft')
            
        PurchaseOrderLine.objects.create(
            order=po,
            material=self.material,
            qty_requested=qty_to_order,
            price_unit=self.material.cost_price
        )

    def scrap(self, qty, reason="Damaged"):
        if self.quantity_on_hand < qty:
            raise ValueError("Not enough stock to scrap")

        with transaction.atomic():
            scrap_loc, _ = StorageLocation.objects.get_or_create(
                location_id="VIRTUAL-SCRAP", 
                defaults={'name': 'Scrap/Loss', 'type': 'loss'}
            )


            StockMove.objects.create(
                material=self.material,
                qty=qty,
                location_source=self.location,
                location_dest=scrap_loc,
                state='done',
                reference=f"Scrap: {reason}"
            )

            self.quantity_on_hand -= qty
            self.save()
            self.evaluate_reorder_rules()

class StockPickingType(TenantAwareModel):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    
    default_source_location = models.ForeignKey(StorageLocation, related_name='default_for_type_src', on_delete=models.SET_NULL, null=True, blank=True)
    default_dest_location = models.ForeignKey(StorageLocation, related_name='default_for_type_dest', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

class StockPicking(TenantAwareModel):
    picking_id = models.CharField(max_length=50, primary_key=True, blank=True)
    picking_type = models.ForeignKey(StockPickingType, on_delete=models.PROTECT)
    origin = models.CharField(max_length=100)
    
    state = models.CharField(
        max_length=20, 
        choices=[('draft', 'Draft'), ('assigned', 'Ready'), ('done', 'Done')], 
        default='draft'
    )


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.picking_id:
            from apps.core.models import SystemSequence
            self.picking_id = SystemSequence.get_next(
                f'inventory.picking.{self.picking_type.code.lower()}', 
                f'WH-{self.picking_type.code}-', 
                5, 
                "Warehouse Pickings"
            )
        super().save(*args, **kwargs)

    def validate_picking(self):
        if self.state == 'done': return

        with transaction.atomic():
            moves = self.moves.all()
            for move in moves:
                if move.state == 'done': continue 

                if move.location_source.type == 'internal':

                    quant = StockQuant.objects.select_for_update().filter(
                        material=move.material, location=move.location_source
                    ).first()
                    if not quant:
                        quant = StockQuant.objects.create(material=move.material, location=move.location_source)
                        
                    quant.quantity_on_hand -= move.qty
                    if quant.quantity_reserved >= move.qty:
                        quant.quantity_reserved -= move.qty
                    else:
                        quant.quantity_reserved = 0
                    quant.save()
                    quant.evaluate_reorder_rules()

                if move.location_dest.type == 'internal':

                    quant = StockQuant.objects.select_for_update().filter(
                        material=move.material, location=move.location_dest
                    ).first()
                    if not quant:
                        quant = StockQuant.objects.create(material=move.material, location=move.location_dest)
                        
                    quant.quantity_on_hand += move.qty
                    if quant.quantity_incoming >= move.qty:
                        quant.quantity_incoming -= move.qty
                    else:
                        quant.quantity_incoming = 0
                    quant.save()

                move.state = 'done'
                move.save() 

            self.state = 'done'
            self.save()

class StockMove(TenantAwareModel):
    STATE_CHOICES = [('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done')]

    move_id = models.CharField(max_length=100, unique=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    
    location_source = models.ForeignKey(StorageLocation, related_name='moves_out', on_delete=models.CASCADE)
    location_dest = models.ForeignKey(StorageLocation, related_name='moves_in', on_delete=models.CASCADE)
    
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='draft')
    reference = models.CharField(max_length=100)

    picking = models.ForeignKey('StockPicking', related_name='moves', on_delete=models.CASCADE, null=True, blank=True)


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.move_id:
            from apps.core.models import SystemSequence
            self.move_id = SystemSequence.get_next('inventory.move', 'MV-', 6, "Stock Moves")

        super().save(*args, **kwargs)
        
        if self.state == 'done':
            self.create_journal_entry()

    def create_journal_entry(self):
        from apps.finance.models import Account, JournalEntry, JournalItem
        
        if JournalEntry.objects.filter(reference__contains=self.move_id).exists():
            return

        try:
            acc_inventory = Account.objects.filter(code='10100').first() or Account.objects.first()
            acc_grni = Account.objects.filter(code='20100').first() or Account.objects.last()
            acc_cogs = Account.objects.filter(code='50000').first() or Account.objects.last()
            if not acc_inventory: return 
        except Exception:
            return 

        value = self.qty * self.material.cost_price
        if value == 0: return


        je = JournalEntry.objects.create(
            date=self.date, 
            reference=f"Stock Move: {self.reference} ({self.move_id})"
        )

        def create_line(account, debit, credit, desc):
            JournalItem.objects.create(entry=je, account=account, debit=debit, credit=credit, description=desc)

        if self.location_source.type == 'supplier' and self.location_dest.type == 'internal':
            create_line(acc_inventory, value, 0, f"{self.material.sku}")
            create_line(acc_grni, 0, value, "Goods Received")

        elif self.location_source.type == 'internal' and self.location_dest.type == 'customer':
            create_line(acc_inventory, 0, value, f"{self.material.sku}")
            create_line(acc_cogs, value, 0, "Cost of Goods Sold")

        elif self.location_source.type == 'internal' and self.location_dest.type == 'loss':
            create_line(acc_inventory, 0, value, f"{self.material.sku}")
            create_line(acc_cogs, value, 0, "Inventory Loss")

        elif self.location_source.type == 'loss' and self.location_dest.type == 'internal':
            create_line(acc_inventory, value, 0, f"{self.material.sku}")
            create_line(acc_cogs, 0, value, "Inventory Gain")

class InventoryAdjustment(TenantAwareModel):
    ref = models.CharField(max_length=50, primary_key=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE)
    state = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('done', 'Applied')], default='draft')
    note = models.TextField(blank=True)


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.ref:
            from apps.core.models import SystemSequence
            self.ref = SystemSequence.get_next('inventory.adjustment', 'AUDIT-', 4, "Inventory Adjustments")
        super().save(*args, **kwargs)

    def apply_adjustment(self):
        if self.state != 'draft': return

        with transaction.atomic():
            adj_loc, _ = StorageLocation.objects.get_or_create(
                location_id="VIRTUAL-ADJ", defaults={'name': 'Inventory Adjustment', 'type': 'loss'}
            )

            for line in self.lines.all():
                quant, _ = StockQuant.objects.get_or_create(material=line.material, location=self.location)
                current_qty = quant.quantity_on_hand
                diff = line.counted_qty - current_qty
                
                if diff == 0: continue 

                if diff > 0:
                    src, dst, qty = adj_loc, self.location, diff
                    quant.quantity_on_hand += qty
                else:
                    src, dst, qty = self.location, adj_loc, abs(diff)
                    quant.quantity_on_hand -= qty


                StockMove.objects.create(
                    material=line.material, qty=qty, location_source=src, location_dest=dst,
                    state='done', reference=f"Adjustment: {self.ref}"
                )
                
                quant.save()
                quant.evaluate_reorder_rules()

            self.state = 'done'
            self.save()

class InventoryAdjustmentLine(TenantAwareModel):
    adjustment = models.ForeignKey(InventoryAdjustment, related_name='lines', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    counted_qty = models.DecimalField(max_digits=12, decimal_places=2)