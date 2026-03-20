from django.db import models

# from django.utils import timezone
# from apps.core.models import Partner, Material # Changed 'Customer' to 'Partner'

# class CustomerOrder(models.Model):
#     order_id = models.CharField(max_length=20, primary_key=True)
#     # Link to the new Partner model, filtered by 'is_customer'
#     customer = models.ForeignKey(Partner, on_delete=models.CASCADE, limit_choices_to={'is_customer': True})
    
#     order_datetime = models.DateTimeField(default=timezone.now)
#     expected_delivery_date = models.DateField(null=True, blank=True)
    
#     # We keep the old simple fields for now, we can link to 'SalesOrder' later
#     material = models.ForeignKey(Material, on_delete=models.CASCADE)
#     qty_ordered = models.IntegerField()
    
#     def __str__(self):
#         return f"{self.order_id} - {self.customer.name}"