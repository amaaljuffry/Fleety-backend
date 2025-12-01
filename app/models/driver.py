from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import List, Optional


class Driver:
    def __init__(self, db):
        self.collection: Collection = db["drivers"]
        self.collection.create_index("user_id")
        self.collection.create_index("vehicle_id")

    def create(self, user_id: str, driver_data: dict):
        driver = {
            "user_id": user_id,
            "name": driver_data.get("name"),
            "email": driver_data.get("email"),
            "phone": driver_data.get("phone"),
            "license_number": driver_data.get("license_number"),
            "license_expiry": driver_data.get("license_expiry"),
            "assigned_vehicles": driver_data.get("assigned_vehicles", []),
            "is_primary": driver_data.get("is_primary", False),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(driver)
        driver["id"] = str(result.inserted_id)
        driver.pop("_id", None)
        return driver

    def get_by_id(self, driver_id: str, user_id: str):
        try:
            driver = self.collection.find_one({
                "_id": ObjectId(driver_id),
                "user_id": user_id
            })
            if driver:
                driver["id"] = str(driver["_id"])
                driver.pop("_id", None)
            return driver
        except Exception:
            return None

    def get_all_by_user(self, user_id: str):
        drivers = list(self.collection.find({"user_id": user_id}))
        result = []
        for d in drivers:
            if "_id" in d:
                d["id"] = str(d["_id"])
                d.pop("_id", None)
                result.append(d)
        return result

    def get_by_vehicle(self, user_id: str, vehicle_id: str):
        drivers = list(self.collection.find({
            "user_id": user_id,
            "assigned_vehicles": vehicle_id
        }))
        result = []
        for d in drivers:
            if "_id" in d:
                d["id"] = str(d["_id"])
                d.pop("_id", None)
                result.append(d)
        return result

    def update(self, driver_id: str, user_id: str, data: dict):
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(driver_id), "user_id": user_id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def assign_vehicle(self, driver_id: str, user_id: str, vehicle_id: str):
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(driver_id), "user_id": user_id},
                {
                    "$addToSet": {"assigned_vehicles": vehicle_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    def unassign_vehicle(self, driver_id: str, user_id: str, vehicle_id: str):
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(driver_id), "user_id": user_id},
                {
                    "$pull": {"assigned_vehicles": vehicle_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, driver_id: str, user_id: str):
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(driver_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False
