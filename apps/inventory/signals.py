from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.store.models import CustomerOrder
from apps.inventory.services import InventoryService

@receiver(post_save, sender=CustomerOrder)
def auto_allocate_on_creation(sender, instance, created, **kwargs):
    """
    Event Listener:
    When an order is created (or updated to 'confirmed'), try to allocate it immediately.
    """

    if created or instance.order_status == CustomerOrder.OrderStatus.CONFIRMED:
        

        if instance.order_status == CustomerOrder.OrderStatus.CONFIRMED:
            print(f"⚡ SIGNAL RECEIVED: Attempting to allocate {instance.order_line_id}...")
            service = InventoryService()
            service.allocate_order(instance.order_line_id)