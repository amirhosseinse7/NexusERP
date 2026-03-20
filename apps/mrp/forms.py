from django import forms
from .models import BillOfMaterial, BomComponent, ManufacturingOrder

class BillOfMaterialForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterial
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '0.01'}),
        }

class BomComponentForm(forms.ModelForm):
    class Meta:
        model = BomComponent
        fields = ['component', 'quantity']
        widgets = {
            'component': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2 text-sm'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2 text-sm', 'step': '0.01'}),
        }

class ManufacturingOrderForm(forms.ModelForm):
    class Meta:
        model = ManufacturingOrder
        fields = ['product', 'bom', 'qty_to_produce']
        widgets = {
            'product': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'bom': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'qty_to_produce': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'step': '1'}),
        }