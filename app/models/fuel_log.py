from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import List, Optional


class FuelLog:
    def __init__(self, db):
        self.collection: Collection = db["fuel_logs"]
        self.collection.create_index("user_id")
        self.collection.create_index("vehicle_id")
        self.collection.create_index([("vehicle_id", 1), ("date", -1)])

    def create(self, user_id: str, vehicle_id: str, fuel_data: dict):
        fuel_log = {
            "user_id": user_id,
            "vehicle_id": vehicle_id,
            # Vehicle & Odometer
            "odometer_reading": fuel_data.get("odometer_reading") or fuel_data.get("mileage"),
            # Fueling Details
            "fuel_type": fuel_data.get("fuel_type", "Petrol RON95"),
            "liters": fuel_data.get("liters") or fuel_data.get("fuel_amount"),
            "price_per_liter": fuel_data.get("price_per_liter") or fuel_data.get("price_per_unit"),
            "total_cost": fuel_data.get("total_cost") or fuel_data.get("total_price"),
            "fuel_station_name": fuel_data.get("fuel_station_name"),
            # Driver & Operational
            "driver_id": fuel_data.get("driver_id"),
            "driver_notes": fuel_data.get("driver_notes"),
            "trip_purpose": fuel_data.get("trip_purpose"),
            # Date & Time
            "date": fuel_data.get("date", datetime.utcnow()),
            "time": fuel_data.get("time"),
            # Evidence & Documentation
            "receipt_url": fuel_data.get("receipt_url"),
            "pump_meter_photo_url": fuel_data.get("pump_meter_photo_url"),
            # Notes
            "notes": fuel_data.get("notes"),
            # Timestamps
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(fuel_log)
        fuel_log["_id"] = str(result.inserted_id)
        return fuel_log

    def get_by_id(self, fuel_log_id: str, user_id: str):
        try:
            fuel_log = self.collection.find_one({
                "_id": ObjectId(fuel_log_id),
                "user_id": user_id
            })
            if fuel_log:
                fuel_log["_id"] = str(fuel_log["_id"])
            return fuel_log
        except Exception:
            return None

    def get_by_vehicle(self, user_id: str, vehicle_id: str, limit: int = 100):
        fuel_logs = list(self.collection.find({
            "user_id": user_id,
            "vehicle_id": vehicle_id
        }).sort("date", -1).limit(limit))
        
        for log in fuel_logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return fuel_logs

    def get_stats(self, user_id: str, vehicle_id: str, days: int = 30):
        """Calculate fuel economy statistics for the given period"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        logs = list(self.collection.find({
            "user_id": user_id,
            "vehicle_id": vehicle_id,
            "date": {"$gte": cutoff_date}
        }).sort("date", 1))

        if len(logs) < 1:
            return {
                "average_mpg": None,
                "total_cost": 0,
                "total_fuel": 0,
                "total_distance": 0,
                "logs_count": len(logs),
                "fuel_type": None,
            }

        total_cost = sum((log.get("total_cost") or log.get("total_price") or 0) for log in logs)
        total_fuel = sum((log.get("liters") or log.get("fuel_amount") or 0) for log in logs)
        
        # Calculate total distance only if odometer_reading data is available
        first_mileage = logs[0].get("odometer_reading") or logs[0].get("mileage")
        last_mileage = logs[-1].get("odometer_reading") or logs[-1].get("mileage")
        total_distance = 0
        if first_mileage and last_mileage:
            total_distance = last_mileage - first_mileage

        average_mpg = total_distance / total_fuel if total_fuel > 0 else None

        return {
            "average_mpg": round(average_mpg, 2) if average_mpg else None,
            "total_cost": round(total_cost, 2),
            "total_fuel": round(total_fuel, 2),
            "total_distance": round(total_distance, 2),
            "logs_count": len(logs),
            "fuel_type": logs[0]["fuel_type"] if logs else None,
        }

    def update(self, fuel_log_id: str, user_id: str, data: dict):
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(fuel_log_id), "user_id": user_id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, fuel_log_id: str, user_id: str):
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(fuel_log_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False
