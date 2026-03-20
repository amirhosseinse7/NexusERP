from django import forms
from .models import PurchaseOrder
from .models import PurchaseOrder, PurchaseOrderLine
from .models import SalesOrder, SalesOrderLine

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier'] 
        widgets = {
            'supplier': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2'}),
        }

class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ['material', 'qty_requested', 'price_unit']
        widgets = {
            'material': forms.Select(attrs={'class': 'border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'}),
            'qty_requested': forms.NumberInput(attrs={'class': 'border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5', 'placeholder': 'Qty'}),
            'price_unit': forms.NumberInput(attrs={'class': 'border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5', 'placeholder': 'Price'}),
        }

class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer', 'delivery_mode']
        widgets = {
            'customer': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2'}),
            'delivery_mode': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2'}),
        }

class SalesOrderLineForm(forms.ModelForm):
    class Meta:
        model = SalesOrderLine
        fields = ['material', 'qty_requested']
        widgets = {
            'material': forms.Select(attrs={'class': 'border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'}),
            'qty_requested': forms.NumberInput(attrs={'class': 'border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5', 'placeholder': 'Qty'}),
        }