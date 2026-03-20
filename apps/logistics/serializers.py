from rest_framework import serializers
from .models import SalesOrder

class SalesOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = SalesOrder

        fields = ['so_id', 'customer', 'customer_name', 'state', 'date_order', 'delivery_mode']
        

        read_only_fields = ['so_id', 'state', 'date_order']