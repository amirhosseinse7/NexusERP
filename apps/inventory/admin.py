from django.contrib import admin
from .models import StorageLocation, StockQuant, StockMove, StockLot

@admin.register(StorageLocation)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('location_id', 'name', 'type', 'parent')
    list_filter = ('type',)

@admin.register(StockQuant)
class QuantAdmin(admin.ModelAdmin):
    list_display = ('material', 'location', 'quantity_on_hand', 'quantity_reserved')
    list_filter = ('location', 'material')

@admin.register(StockMove)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('date', 'reference', 'material', 'qty', 'location_source', 'location_dest', 'state')
    list_filter = ('state', 'date')