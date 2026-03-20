from django.contrib import admin
from .models import Material, Partner, ProductCategory, UoM

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'min_stock_level', 'quantity_available_preview')
    search_fields = ('sku', 'name')
    list_filter = ('category',)
    

    def quantity_available_preview(self, obj):

        return "-" 
    quantity_available_preview.short_description = "Stock Est."

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('partner_id', 'name', 'is_customer', 'is_supplier', 'city_preview')
    list_filter = ('is_customer', 'is_supplier')
    search_fields = ('name', 'partner_id')

    def city_preview(self, obj):
        return "📍 Location Set" if obj.latitude else "No Location"
    city_preview.short_description = "Geo"

@admin.register(ProductCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')

@admin.register(UoM)
class UoMAdmin(admin.ModelAdmin):
    list_display = ('name', 'ratio')