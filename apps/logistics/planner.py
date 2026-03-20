from django.utils import timezone
from django.db import transaction
from apps.logistics.models import OutboundShipment, Vehicle, DeliveryRoute

class LogisticPlanner:
    def assign_routes(self):
        print("🚚 Planner: Starting Route Optimization...")
        

        pending = OutboundShipment.objects.filter(route__isnull=True)
        if not pending.exists():
            print("   ✅ No pending shipments to route.")
            return

        print(f"   📦 Found {pending.count()} unassigned shipments.")


        vans = Vehicle.objects.filter(mode__mode_id='van', is_active=True)
        bikes = Vehicle.objects.filter(mode__mode_id='bike', is_active=True)
        

        self._fill_vehicles(pending, vans, max_capacity=800)
        

        remaining = OutboundShipment.objects.filter(route__isnull=True)
        if remaining.exists():
             self._fill_vehicles(remaining, bikes, max_capacity=50)

    def _fill_vehicles(self, shipments, vehicles, max_capacity):
        for vehicle in vehicles:
            current_load = 0
            route_shipments = []
            

            route_id = f"RTE-{timezone.now().strftime('%Y%m%d')}-{vehicle.vehicle_id}"
            

            if DeliveryRoute.objects.filter(route_id=route_id).exists():
                continue

            for ship in shipments:

                ship.refresh_from_db()
                if ship.route: continue
                
                weight = ship.material.default_unit_weight_kg
                

                if current_load + weight <= max_capacity:
                    current_load += weight
                    route_shipments.append(ship)
                

                if current_load >= max_capacity:
                    break 
            

            if route_shipments:
                with transaction.atomic():
                    route = DeliveryRoute.objects.create(
                        route_id=route_id,
                        vehicle=vehicle,
                        date=timezone.now().date(),
                        start_time=timezone.now()
                    )
                    

                    for s in route_shipments:
                        s.route = route
                        s.save()
                        
                print(f"   🚛 Assigned {len(route_shipments)} orders to {vehicle.vehicle_id} (Load: {current_load}kg / {max_capacity}kg)")