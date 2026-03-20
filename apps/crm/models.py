from django.db import models
from django.utils import timezone
from django.db import transaction


from apps.core.models import TenantAwareModel


from simple_history.models import HistoricalRecords

class Opportunity(TenantAwareModel):
    STATE_CHOICES = [
        ('new', 'New Lead'),
        ('qualified', 'Qualified'),
        ('won', 'Won'),
        ('lost', 'Lost')
    ]

    opp_id = models.CharField(max_length=50, primary_key=True, blank=True)
    title = models.CharField(max_length=200, help_text="e.g., Summer Restock Order")
    
    customer = models.ForeignKey('core.Partner', on_delete=models.CASCADE, limit_choices_to={'is_customer': True})
    
    
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    probability = models.IntegerField(default=10, help_text="Probability of winning (%)")
    
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='new')
    date_created = models.DateTimeField(default=timezone.now)

    sales_order = models.ForeignKey('logistics.SalesOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')

    
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        
        if not self.opp_id:
            from apps.core.models import SystemSequence
            self.opp_id = SystemSequence.get_next('crm.opportunity', 'OPP-', 4, "Sales Opportunities")
        super().save(*args, **kwargs)

    def convert_to_sales_order(self):
        """
        Instantly generates a Sales Order and transfers all line items!
        """
        from apps.logistics.models import SalesOrder, SalesOrderLine
        
        if self.sales_order:
            return self.sales_order 

        with transaction.atomic():
            
            so = SalesOrder.objects.create(
                customer=self.customer,
                state='draft',
                delivery_mode='normal'
            )
            
            
            for line in self.lines.all():
                SalesOrderLine.objects.create(
                    order=so,
                    material=line.material,
                    qty_requested=line.quantity,
                    price_unit=line.price_unit
                )

            
            self.sales_order = so
            self.state = 'won'
            self.save()
            
        return so

    def __str__(self):
        return f"{self.opp_id} - {self.title}"


class OpportunityLine(TenantAwareModel):
    opportunity = models.ForeignKey(Opportunity, related_name='lines', on_delete=models.CASCADE)
    material = models.ForeignKey('core.Material', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1.0)
    price_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


    history = HistoricalRecords()

    @property
    def subtotal(self):
        return self.quantity * self.price_unit