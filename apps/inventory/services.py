from django.db import transaction
from django.db.models import F
from apps.inventory.models import InventoryDaily
from apps.store.models import CustomerOrder
from apps.logistics.services import LogisticsEngine 

class InventoryService:
    """
    Handles Stock Deductions and Warehouse Selection.
    """
    
    def allocate_order(self, order_id):
        """
        The Brain: Finds the best warehouse for a specific order.
        """
        try:
            order = CustomerOrder.objects.select_for_update().get(order_line_id=order_id)
        except CustomerOrder.DoesNotExist:
            return False


        latest_date = InventoryDaily.objects.latest('date').date
        
        candidates = InventoryDaily.objects.filter(
            date=latest_date,
            material=order.material,
            closing_on_hand_units__gte=order.qty_units
        ).select_related('warehouse')

        if not candidates.exists():

            order.order_status = CustomerOrder.OrderStatus.BACKORDER
            order.notes += " | System: No Stock Available"
            order.save()
            return False


        best_wh = None
        min_dist = float('inf')
        logistics = LogisticsEngine()

        for record in candidates:
            dist = logistics.calculate_haversine(
                order.customer.customer_lat, order.customer.customer_lon,
                record.warehouse.lat, record.warehouse.lon
            )
            
            if dist < min_dist:
                min_dist = dist
                best_wh = record


        if best_wh:
            with transaction.atomic():

                locked_stock = InventoryDaily.objects.select_for_update().get(
                    id=best_wh.id 
                )
                
                if locked_stock.closing_on_hand_units >= order.qty_units:

                    locked_stock.closing_on_hand_units = F('closing_on_hand_units') - order.qty_units
                    locked_stock.save()
                    

                    order.order_status = CustomerOrder.OrderStatus.ALLOCATED
                    order.notes += f" | Allocated from {best_wh.warehouse.name} ({min_dist}km)"
                    order.save()
                    return True
                else:

                    return False
        
        return False