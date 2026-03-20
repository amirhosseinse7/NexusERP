from django import forms
from apps.core.models import Material, Partner
from .models import InventoryAdjustment, InventoryAdjustmentLine, StorageLocation

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            'sku', 'name', 'category', 'uom', 
            'cost_price', 'sales_price', 
            'min_stock_level', 'max_stock_level', 'lead_time_days',
            'abc_class', 'forecast_30d', 'churn_rate', 'supplier_perf',

            'auto_reorder', 'custom_reorder_qty', 'preferred_supplier'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2 focus:ring-blue-500 focus:border-blue-500'}),
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'category': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'uom': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'cost_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '0.01'}),
            'sales_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '0.01'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'max_stock_level': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'lead_time_days': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'abc_class': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'forecast_30d': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'churn_rate': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '0.1'}),
            'supplier_perf': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '0.1'}),
            

            'auto_reorder': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 cursor-pointer mt-2'}),
            'custom_reorder_qty': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'Leave blank to fill to Max Level'}),
            'preferred_supplier': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
        }

class InventoryAdjustmentForm(forms.ModelForm):
    class Meta:
        model = InventoryAdjustment
        fields = ['ref', 'location', 'note']
        widgets = {
            'ref': forms.TextInput(attrs={
                'class': 'w-full border-gray-300 rounded-lg p-2', 
                'placeholder': 'Leave empty to auto-generate'
            }),
            'location': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'note': forms.Textarea(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['ref'].required = False 
        

        from .models import StorageLocation
        self.fields['location'].queryset = StorageLocation.objects.filter(type='internal')

class AdjustmentLineForm(forms.ModelForm):
    class Meta:
        model = InventoryAdjustmentLine
        fields = ['material', 'counted_qty']
        widgets = {
            'material': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'counted_qty': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
        }

class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ['location_id', 'name', 'type']
        widgets = {
            'location_id': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'e.g., WH-NY'}),
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'e.g., New York Branch'}),
            'type': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
        }