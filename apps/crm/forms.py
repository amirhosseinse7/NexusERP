from django import forms
from .models import Opportunity, OpportunityLine

class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        
        fields = ['title', 'customer', 'probability']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'e.g., 500 Laptops for Q4'}),
            'customer': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'probability': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'min': '0', 'max': '100'}),
        }

class OpportunityLineForm(forms.ModelForm):
    class Meta:
        model = OpportunityLine
        fields = ['material', 'quantity']
        widgets = {
            'material': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2 text-sm'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2 text-sm', 'step': '1'}),
        }