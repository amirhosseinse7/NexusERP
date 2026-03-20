# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.db import transaction
# from apps.inventory.models import StockMove
# from apps.finance.models import JournalEntry, JournalItem, Account
# import uuid

# @receiver(post_save, sender=StockMove)
# def create_valuation_entry(sender, instance, created, **kwargs):
#     """
#     Trigger: Whenever a StockMove is created with state='done'.
#     Action: Create the Financial Journal Entry automatically.
#     """
#     move = instance
#     if not created or move.state != 'done':
#         return

#     # Calculate Value
#     # Formula: Qty * Standard Cost
#     value = move.qty * move.material.cost_price
    
#     if value == 0:
#         return

#     with transaction.atomic():
#         # 1. Identify Accounts (Hardcoded Standard Commercial Setup for now)
#         try:
#             acc_inventory = Account.objects.get(code="10100") # Asset
#             acc_grni = Account.objects.get(code="20100")      # Liability (Goods Received Not Invoiced)
#             acc_cogs = Account.objects.get(code="50000")      # Expense (Cost of Goods Sold)
#         except Account.DoesNotExist:
#             print("⚠️ Accounts missing! Skipping Valuation.")
#             return

#         # 2. Create Header
#         je = JournalEntry.objects.create(
#             entry_id=f"JE-{move.move_id}",
#             reference=f"Stock Move: {move.reference}"
#         )

#         # 3. Determine Flow based on Location Type
#         source_type = move.location_source.type
#         dest_type = move.location_dest.type

#         # SCENARIO A: INBOUND (Vendor -> Warehouse)
#         # Result: Increase Asset (Debit), Increase Liability (Credit)
#         if source_type == 'supplier' and dest_type == 'internal':
#             JournalItem.objects.create(entry=je, account=acc_inventory, debit=value, credit=0)
#             JournalItem.objects.create(entry=je, account=acc_grni, debit=0, credit=value)
#             print(f"💰 Financial Entry Created: +${value} Inventory")

#         # SCENARIO B: OUTBOUND (Warehouse -> Customer)
#         # Result: Increase Expense (Debit), Decrease Asset (Credit)
#         elif source_type == 'internal' and dest_type == 'customer':
#             JournalItem.objects.create(entry=je, account=acc_cogs, debit=value, credit=0)
#             JournalItem.objects.create(entry=je, account=acc_inventory, debit=0, credit=value)
#             print(f"💰 Financial Entry Created: +${value} COGS")