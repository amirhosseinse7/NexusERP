import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.core.models import Customer, Material, Location
from apps.store.models import CustomerOrder
from apps.inventory.models import InventoryDaily

class Command(BaseCommand):
    help = 'Wipes transactional data and loads the 90-day simulation.'

    def handle(self, *args, **kwargs):
        data_dir = os.path.join(settings.BASE_DIR, 'data_simulation')
        
        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR("❌ 'data_simulation' folder not found. Run generate_scenario.py first."))
            return


        self.stdout.write("🧹 Wiping old transactional data...")
        CustomerOrder.objects.all().delete()
        InventoryDaily.objects.all().delete()
        Customer.objects.all().delete()
        

        self.stdout.write("... Loading Customers")
        with open(f'{data_dir}/customers.csv', 'r') as f:
            reader = csv.DictReader(f)
            objs = [
                Customer(
                    customer_id=row['customer_id'],
                    home_store_id=row['home_store_id'],
                    customer_lat=float(row['customer_lat']),
                    customer_lon=float(row['customer_lon']),
                    is_online_customer=True
                )
                for row in reader
            ]

            Customer.objects.bulk_create(objs, ignore_conflicts=True)


        self.stdout.write("... Loading Inventory History")
        wh, _ = Location.objects.get_or_create(
            location_id="WH_NCL_01",
            defaults={'name': 'Newcastle DC', 'location_type': 'warehouse', 'lat': 54.97, 'lon': -1.61}
        )
        
        inv_objs = []
        with open(f'{data_dir}/warehouse_daily_inventory.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    mat = Material.objects.get(material_id=row['material_id'])
                    inv_objs.append(InventoryDaily(
                        run_id=row['run_id'],
                        scenario=row['scenario'],
                        date=row['date'],
                        warehouse=wh,
                        material=mat,
                        opening_on_hand_units=float(row['opening_on_hand_units']),
                        closing_on_hand_units=float(row['closing_on_hand_units']),
                        demand_units=float(row['demand_units']),
                        served_units=float(row['served_units'])
                    ))
                except Material.DoesNotExist:
                    continue 


        InventoryDaily.objects.bulk_create(inv_objs, batch_size=1000, ignore_conflicts=True)


        self.stdout.write("... Loading Orders (This might take a moment)")
        order_objs = []
        with open(f'{data_dir}/customer_orders.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cust = Customer.objects.get(customer_id=row['customer_id'])
                    mat = Material.objects.get(material_id=row['material_id'])
                    order_objs.append(CustomerOrder(
                        order_line_id=row['order_line_id'],
                        order_id=row['order_id'],
                        customer=cust,
                        material=mat,
                        order_datetime=row['order_datetime'],
                        qty_units=int(row['qty_units']),
                        unit_price_gbp=float(row['unit_price_gbp']),
                        order_status=row['order_status'],
                        delivery_postcode=row['delivery_postcode']
                    ))
                except Exception:
                    continue
        

        CustomerOrder.objects.bulk_create(order_objs, batch_size=1000, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS("✅ 90-Day Simulation Loaded Successfully!"))