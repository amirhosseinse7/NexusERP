import math
from apps.core.models import Location, DeliveryMode
from apps.store.models import CustomerOrder
from django.db.models import Sum

class LogisticsEngine:
    """
    Pure Logic Service for Distance Calculations and Route Optimization.
    Does NOT write to the database. It only calculates and returns plans.
    """

    @staticmethod
    def calculate_haversine(lat1, lon1, lat2, lon2):
        """Returns distance in KM between two coordinates."""
        if any(x is None for x in [lat1, lon1, lat2, lon2]):
            return 0.0
        
        R = 6371  
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    def route_orders_for_zone(self, zone_prefix, warehouse_id):
        """
        1. Fetch all 'ALLOCATED' orders for this warehouse & zone.
        2. Sort them by distance (Milk Run / Sweep).
        3. Select best vehicle.
        """
       
        warehouse = Location.objects.get(location_id=warehouse_id)
        orders = CustomerOrder.objects.filter(
            order_status=CustomerOrder.OrderStatus.ALLOCATED,
            delivery_postcode__startswith=zone_prefix

        )

        if not orders.exists():
            return None


        stops = []
        total_weight = 0
        
        for order in orders:
            dist = self.calculate_haversine(
                warehouse.lat, warehouse.lon,
                order.customer.customer_lat, order.customer.customer_lon
            )
            weight = order.qty_units * order.material.default_unit_weight_kg
            
            stops.append({
                'order': order,
                'dist_from_wh': dist,
                'weight': weight,
                'lat': order.customer.customer_lat,
                'lon': order.customer.customer_lon
            })
            total_weight += weight


        stops.sort(key=lambda x: x['dist_from_wh'])


        total_dist = 0
        current_lat, current_lon = warehouse.lat, warehouse.lon
        
        for stop in stops:
            leg_dist = self.calculate_haversine(current_lat, current_lon, stop['lat'], stop['lon'])
            total_dist += leg_dist
            current_lat, current_lon = stop['lat'], stop['lon']
            

        total_dist += self.calculate_haversine(current_lat, current_lon, warehouse.lat, warehouse.lon)


        best_mode = self._select_mode(total_dist, total_weight)

        return {
            'route_id': f"RT_{zone_prefix}_{warehouse_id}",
            'stops': stops,
            'total_dist': round(total_dist, 2),
            'total_weight': round(total_weight, 2),
            'vehicle': best_mode
        }

    def _select_mode(self, distance, weight):
        """Finds the cheapest vehicle that fits the load."""
        modes = DeliveryMode.objects.all()
        best_mode = None
        min_cost = float('inf')

        for mode in modes:

            if weight > mode.max_weight_kg: continue
            if distance > mode.max_radius_km: continue
            

            cost = distance * mode.cost_per_km_gbp
            if cost < min_cost:
                min_cost = cost
                best_mode = mode

        return best_mode