import django_filters
from django import forms
from apps.core.models import Material, ProductCategory

class ProductFilter(django_filters.FilterSet):

    category = django_filters.ModelChoiceFilter(
        queryset=ProductCategory.objects.all(),
        field_name='category',
        to_field_name='name',
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'bg-white border border-gray-300 text-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    

    query = django_filters.CharFilter(
        method='custom_search',
        widget=forms.TextInput(attrs={
            'class': 'w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Search by Name or SKU...'
        })
    )

    class Meta:
        model = Material
        fields = ['category']

    def custom_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(Q(name__icontains=value) | Q(sku__icontains=value))