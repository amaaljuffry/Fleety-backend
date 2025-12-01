from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import List, Optional


class Vehicle:
    def __init__(self, db):
        self.collection: Collection = db["vehicles"]
        self.collection.create_index("user_id")

    def create(self, user_id: str, vehicle_data: dict):
        vehicle = {
            "user_id": user_id,
            "make": vehicle_data.get("make"),
            "model": vehicle_data.get("model"),
            "year": vehicle_data.get("year"),
            "color": vehicle_data.get("color"),
            "vin": vehicle_data.get("vin"),
            "license_plate": vehicle_data.get("license_plate"),
            "current_mileage": vehicle_data.get("current_mileage", 0),
            "image_url": vehicle_data.get("image_url"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(vehicle)
        vehicle["_id"] = str(result.inserted_id)
        return vehicle

    def get_by_id(self, vehicle_id: str, user_id: str):
        try:
            vehicle = self.collection.find_one({
                "_id": ObjectId(vehicle_id),
                "user_id": user_id
            })
            if vehicle:
                vehicle["_id"] = str(vehicle["_id"])
            return vehicle
        except Exception:
            return None

    def get_all_by_user(self, user_id: str):
        vehicles = list(self.collection.find({"user_id": user_id}))
        result = []
        for v in vehicles:
            if "_id" in v:
                v["_id"] = str(v["_id"])
                result.append(v)
        return result

    def update(self, vehicle_id: str, user_id: str, data: dict):
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(vehicle_id), "user_id": user_id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, vehicle_id: str, user_id: str):
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(vehicle_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False
