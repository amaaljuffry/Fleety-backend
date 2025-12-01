from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import List, Optional


class Maintenance:
    def __init__(self, db):
        self.collection: Collection = db["maintenance"]
        self.collection.create_index("vehicle_id")
        self.collection.create_index("user_id")

    def create(self, user_id: str, vehicle_id: str, maintenance_data: dict):
        maintenance = {
            "user_id": user_id,
            "vehicle_id": vehicle_id,
            "date": datetime.fromisoformat(maintenance_data.get("date")),
            "service_type": maintenance_data.get("service_type"),
            "description": maintenance_data.get("description"),
            "mileage": maintenance_data.get("mileage", 0),
            "cost": maintenance_data.get("cost", 0),
            "service_provider": maintenance_data.get("service_provider", ""),
            "notes": maintenance_data.get("notes", ""),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(maintenance)
        maintenance["id"] = str(result.inserted_id)
        maintenance.pop("_id", None)
        return maintenance

    def get_by_id(self, maintenance_id: str, user_id: str):
        try:
            record = self.collection.find_one({
                "_id": ObjectId(maintenance_id),
                "user_id": user_id
            })
            if record:
                record["id"] = str(record["_id"])
                record.pop("_id", None)
            return record
        except Exception:
            return None

    def get_by_vehicle(self, vehicle_id: str, user_id: str):
        records = list(self.collection.find({
            "vehicle_id": vehicle_id,
            "user_id": user_id
        }).sort("date", -1))
        return [
            {**r, "id": str(r["_id"])} for r in records if "_id" in r
        ]

    def update(self, maintenance_id: str, user_id: str, data: dict):
        try:
            if "date" in data and isinstance(data["date"], str):
                data["date"] = datetime.fromisoformat(data["date"])
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(maintenance_id), "user_id": user_id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, maintenance_id: str, user_id: str):
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(maintenance_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False
