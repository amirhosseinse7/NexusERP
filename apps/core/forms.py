from django import forms
from .models import Partner

class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner

        fields = ['name', 'email', 'phone', 'address', 'is_customer', 'is_supplier']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'phone': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'address': forms.Textarea(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'rows': 3}),
            'is_customer': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'}),
            'is_supplier': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'}),
        }