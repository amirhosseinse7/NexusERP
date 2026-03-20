from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine, Vehicle

class POLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1

class SOLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1

@admin.register(PurchaseOrder)
class POAdmin(admin.ModelAdmin):
    list_display = ('po_id', 'supplier', 'date_order', 'state')
    inlines = [POLineInline]
    actions = ['mark_confirmed', 'mark_received']


    def mark_confirmed(self, request, queryset):
        for po in queryset: po.confirm_order()
    def mark_received(self, request, queryset):
        for po in queryset: po.receive_order()

@admin.register(SalesOrder)
class SOAdmin(admin.ModelAdmin):
    list_display = ('so_id', 'customer', 'delivery_mode', 'state')
    inlines = [SOLineInline]
    actions = ['mark_confirmed', 'mark_shipped']

    def mark_confirmed(self, request, queryset):
        for so in queryset: 
            try: so.confirm_order()
            except ValueError as e: self.message_user(request, str(e), level='error')

    def mark_shipped(self, request, queryset):
        for so in queryset: so.ship_order()

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_id', 'max_weight_kg', 'is_active')