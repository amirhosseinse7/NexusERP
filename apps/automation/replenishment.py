from django.db.models import Sum
from apps.core.models import Material, Partner
from apps.inventory.models import StockQuant
from apps.logistics.models import PurchaseOrder, PurchaseOrderLine
import math

class AutoReplenishmentService:

    def run_cycle(self):
        print("🔄 MRP Cycle Started...")
        

        materials = Material.objects.all()

        for material in materials:
            self.check_and_replenish(material)
            
        print("✅ MRP Cycle Finished.")

    def check_and_replenish(self, material):
        print(f"   🔎 Analyzing: {material.name} ({material.sku})")


        aggregates = StockQuant.objects.filter(material=material).aggregate(
            total_on_hand=Sum('quantity_on_hand'),
            total_incoming=Sum('quantity_incoming')
        )
        

        qty_on_hand = aggregates['total_on_hand'] or 0
        qty_incoming = aggregates['total_incoming'] or 0
        

        effective_stock = qty_on_hand + qty_incoming
        

        min_stock = material.min_stock_level
        max_stock = material.max_stock_level
        
        print(f"      📊 Stats: Hand={qty_on_hand} | Incoming={qty_incoming} | Total={effective_stock}")
        print(f"      🎯 Rules: Min={min_stock} | Max={max_stock}")

        if effective_stock < min_stock:

            shortfall = max_stock - effective_stock
            
            if shortfall <= 0:
                return 

            print(f"      🚨 STOCK ALERT! Below Minimum. Ordering {shortfall} units.")
            self.create_purchase_order(material, shortfall)
        else:
            print("      ✅ Stock Level Healthy.")

    def create_purchase_order(self, material, qty):


        supplier = Partner.objects.filter(is_supplier=True).first()
        
        if not supplier:
            print("      ⚠️ Error: No Supplier found in database. Cannot order.")
            return


        po = PurchaseOrder.objects.create(
            supplier=supplier,
            state='draft' 
        )
        

        PurchaseOrderLine.objects.create(
            order=po,
            material=material,
            qty_requested=qty,
            price_unit=material.cost_price
        )
        
        print(f"      📝 GENERATED: {po.po_id} for {supplier.name}")