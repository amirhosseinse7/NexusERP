from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.automation.services import DemandForecaster
from apps.store.models import CustomerOrder

class Command(BaseCommand):
    help = 'Trains the AI and predicts demand for the highest volume product'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Starting Demand Forecasting Engine...")
        

        top_material = (
            CustomerOrder.objects
            .values('material_id')
            .annotate(total_orders=Count('order_line_id'))
            .order_by('-total_orders')
            .first()
        )

        if not top_material:
            self.stdout.write(self.style.ERROR("❌ No orders found in database. Run load_simulation first."))
            return

        target_material_id = top_material['material_id']
        order_count = top_material['total_orders']

        self.stdout.write(f"📊 Top Product Detected: {target_material_id} ({order_count} orders)")
        

        forecaster = DemandForecaster()
        forecast = forecaster.generate_forecast(target_material_id)
        
        if "error" in forecast:
            self.stdout.write(self.style.WARNING(f"⚠️ {forecast['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Forecast for {target_material_id}:"))
            for day in forecast:
                self.stdout.write(f"   📅 {day['date']}: Expecting {day['predicted_qty']} units")

        self.stdout.write("🏁 Forecasting Complete.")