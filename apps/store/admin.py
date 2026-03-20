from django.contrib import admin

# from .models import CustomerOrder
# from apps.logistics.services import LogisticsEngine
# from apps.logistics.models import OutboundShipment
# from apps.core.models import Location, DeliveryMode # Needed for saving results

# @admin.action(description='Generate Route for Selected Orders')
# def run_routing_engine(modeladmin, request, queryset):
#     """
#     Admin Action: Takes selected orders -> Runs LogisticsEngine -> Creates Shipments.
#     """
#     # 1. Filter for VALID orders only (Must be Allocated, not yet Shipped)
#     valid_orders = queryset.filter(order_status=CustomerOrder.OrderStatus.ALLOCATED)
    
#     if not valid_orders.exists():
#         modeladmin.message_user(request, "No 'ALLOCATED' orders selected!", messages.ERROR)
#         return

#     # 2. Group by Zone + Warehouse (Simplified for the prototype)
#     # We grab the first order's details to define the batch context
#     first_order = valid_orders.first()
    
#     # Extract the Zone Prefix (e.g., "NE1" from "NE1 4XX")
#     zone_prefix = first_order.delivery_postcode.split(' ')[0]
    
#     # We need to find WHICH warehouse these orders are allocated from.
#     # In our current prototype, we stored that in the 'notes'. 
#     # To be robust, we'll assume they are from the *same* warehouse for this test.
#     # In a real app, you'd group them programmatically.
    
#     # Hack: Let's pretend we know the warehouse ID from the note or just pick the first one from DB
#     # For this test, we will hardcode the warehouse ID used in your seed data or previous test
#     # (Check your specific warehouse ID in the 'Locations' table if this fails)
#     warehouse_id = "WH_NCL_01" 

#     # 3. Call the Engine
#     engine = LogisticsEngine()
#     plan = engine.route_orders_for_zone(zone_prefix, warehouse_id)
    
#     if not plan:
#         modeladmin.message_user(request, "Routing Engine returned no plan.", messages.WARNING)
#         return

#     # 4. Save the Result (Create Outbound Shipments)
#     shipment_count = 0
#     warehouse_obj = Location.objects.get(location_id=warehouse_id)
    
#     for stop in plan['stops']:
#         order = stop['order']
        
#         OutboundShipment.objects.create(
#             run_id="MANUAL_ADMIN_RUN",
#             scenario="RealTime",
#             order_line_id=order.order_line_id,
#             warehouse=warehouse_obj,
#             material=order.material,
#             delivery_mode=plan['vehicle'],
#             ship_date=first_order.order_datetime.date(),
#             distance_km=stop['dist_from_wh'],
#             transport_cost_gbp_est=0.0, # You can add cost logic here
#         )
        
#         # Update Order Status
#         order.order_status = CustomerOrder.OrderStatus.SHIPPED
#         order.notes += f" | Routed via {plan['vehicle'].mode_id} (Route {plan['route_id']})"
#         order.save()
#         shipment_count += 1

#     modeladmin.message_user(request, f"Successfully routed {shipment_count} orders via {plan['vehicle'].description}!", messages.SUCCESS)


# @admin.register(CustomerOrder)
# class CustomerOrderAdmin(admin.ModelAdmin):
#     list_display = ('order_line_id', 'order_status', 'material', 'qty_units', 'delivery_postcode', 'notes')
#     list_filter = ('order_status', 'delivery_postcode')
#     search_fields = ('order_line_id',)
#     actions = [run_routing_engine] # <--- Add the action here