import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import timedelta
from django.utils import timezone
from apps.store.models import CustomerOrder
from apps.core.models import Material

class DemandForecaster:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)

    def generate_forecast(self, material_id=None):
        """
        Trains a model on historical orders and predicts the next 7 days.
        """
        print(f"🧠 AI: Starting Forecast for {material_id if material_id else 'ALL Materials'}...")


        orders = CustomerOrder.objects.all().values('order_datetime', 'material_id', 'qty_units')
        df = pd.DataFrame(orders)

        if df.empty:
            return {"error": "Not enough data to train."}

        df['date'] = pd.to_datetime(df['order_datetime']).dt.date
        

        if material_id:
            df = df[df['material_id'] == material_id]

        daily_demand = df.groupby(['date', 'material_id'])['qty_units'].sum().reset_index()


        daily_demand['day_of_week'] = pd.to_datetime(daily_demand['date']).dt.dayofweek
        daily_demand['day_of_year'] = pd.to_datetime(daily_demand['date']).dt.dayofyear
        daily_demand['month'] = pd.to_datetime(daily_demand['date']).dt.month
        

        X = daily_demand[['day_of_week', 'day_of_year', 'month']]
        y = daily_demand['qty_units']

        if len(X) < 5:
            return {"error": "Need at least 5 days of history to train AI."}


        self.model.fit(X, y)


        future_dates = [timezone.now().date() + timedelta(days=i) for i in range(1, 8)]
        predictions = []

        for date in future_dates:
            features = [[date.weekday(), date.timetuple().tm_yday, date.month]]
            pred_qty = self.model.predict(features)[0]
            predictions.append({
                "date": date,
                "predicted_qty": round(pred_qty, 2)
            })

        return predictions