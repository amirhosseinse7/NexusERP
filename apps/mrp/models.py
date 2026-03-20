from django.db import models
from django.utils import timezone
from django.db import transaction


from apps.core.models import TenantAwareModel


from simple_history.models import HistoricalRecords

# ==========================================
# BILL OF MATERIALS (The Recipe)
# ==========================================

class BillOfMaterial(TenantAwareModel):
    bom_id = models.CharField(max_length=50, primary_key=True, blank=True)
    product = models.ForeignKey('core.Material', related_name='boms', on_delete=models.CASCADE, help_text="The finished product being created")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.0, help_text="Base quantity produced by this recipe")
    

    history = HistoricalRecords()
    
    def save(self, *args, **kwargs):

        if not self.bom_id:
            from apps.core.models import SystemSequence
            self.bom_id = SystemSequence.get_next('mrp.bom', 'BOM-', 4, "Bill of Materials")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bom_id} - {self.product.name}"

class BomComponent(TenantAwareModel):
    bom = models.ForeignKey(BillOfMaterial, related_name='components', on_delete=models.CASCADE)
    component = models.ForeignKey('core.Material', on_delete=models.CASCADE, help_text="The raw material needed")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity required to make the base BOM quantity")


    history = HistoricalRecords()

# ==========================================
# MANUFACTURING ORDERS (The Factory Floor)
# ==========================================

class ManufacturingOrder(TenantAwareModel):
    STATE_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed / In Progress'),
        ('done', 'Done'),
    ]
    
    mo_id = models.CharField(max_length=50, primary_key=True, blank=True)
    product = models.ForeignKey('core.Material', on_delete=models.CASCADE)
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.PROTECT)
    qty_to_produce = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='draft')
    date_created = models.DateTimeField(default=timezone.now)


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.mo_id:
            from apps.core.models import SystemSequence
            self.mo_id = SystemSequence.get_next('mrp.mo', 'MO-', 4, "Manufacturing Orders")
        super().save(*args, **kwargs)

    def produce(self):
        if self.state == 'done':
            return
            
        from apps.inventory.models import StockQuant, StockMove, StorageLocation
        
        with transaction.atomic():
            prod_loc, _ = StorageLocation.objects.get_or_create(
                location_id='VIRTUAL-PROD', 
                defaults={'name': 'Production Facility', 'type': 'production'}
            )
            
            main_loc = StorageLocation.objects.filter(type='internal').first()
            if not main_loc:
                main_loc, _ = StorageLocation.objects.get_or_create(
                    location_id='WH-STOCK', 
                    defaults={'name': 'Main Warehouse', 'type': 'internal'}
                )

            multiplier = self.qty_to_produce / self.bom.quantity


            for comp in self.bom.components.all():
                consumed_qty = comp.quantity * multiplier
                

                quant = StockQuant.objects.select_for_update().filter(
                    material=comp.component, location=main_loc
                ).first()
                if not quant:
                    quant = StockQuant.objects.create(material=comp.component, location=main_loc)

                if quant.quantity_on_hand < consumed_qty:
                    raise ValueError(f"Not enough stock of {comp.component.name}. Needed: {consumed_qty}, Available: {quant.quantity_on_hand}")
                
                StockMove.objects.create(
                    material=comp.component,
                    qty=consumed_qty,
                    location_source=main_loc,
                    location_dest=prod_loc,
                    state='done',
                    reference=f"MO Consumption: {self.mo_id}"
                )
                
                quant.quantity_on_hand -= consumed_qty
                quant.save()


            StockMove.objects.create(
                material=self.product,
                qty=self.qty_to_produce,
                location_source=prod_loc,
                location_dest=main_loc,
                state='done',
                reference=f"MO Production: {self.mo_id}"
            )
            

            fg_quant = StockQuant.objects.select_for_update().filter(
                material=self.product, location=main_loc
            ).first()
            if not fg_quant:
                fg_quant = StockQuant.objects.create(material=self.product, location=main_loc)
                
            fg_quant.quantity_on_hand += self.qty_to_produce
            fg_quant.save()

            self.state = 'done'
            self.save()

    def __str__(self):
        return f"{self.mo_id} - {self.product.name}"