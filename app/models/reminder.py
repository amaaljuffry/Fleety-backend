from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import Optional


class Reminder:
    def __init__(self, db):
        self.collection: Collection = db["reminders"]
        self.collection.create_index("vehicle_id")
        self.collection.create_index("user_id")

    def create(self, user_id: str, vehicle_id: str, reminder_data: dict):
        reminder = {
            "user_id": user_id,
            "vehicle_id": vehicle_id,
            "service_type": reminder_data.get("service_type"),
            "description": reminder_data.get("description", ""),
            "due_by_mileage": reminder_data.get("due_by_mileage"),
            "due_by_date": datetime.fromisoformat(reminder_data.get("due_by_date")) if reminder_data.get("due_by_date") else None,
            "reminder_threshold_miles": reminder_data.get("reminder_threshold_miles", 0),
            "reminder_threshold_days": reminder_data.get("reminder_threshold_days", 0),
            "is_recurring": reminder_data.get("is_recurring", False),
            "recurring_interval_miles": reminder_data.get("recurring_interval_miles"),
            "recurring_interval_months": reminder_data.get("recurring_interval_months"),
            "last_completed_date": datetime.fromisoformat(reminder_data.get("last_completed_date")) if reminder_data.get("last_completed_date") else None,
            "last_completed_mileage": reminder_data.get("last_completed_mileage"),
            "is_active": reminder_data.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(reminder)
        reminder["id"] = str(result.inserted_id)
        reminder.pop("_id", None)
        return reminder

    def get_by_id(self, reminder_id: str, user_id: str):
        try:
            reminder = self.collection.find_one({
                "_id": ObjectId(reminder_id),
                "user_id": user_id
            })
            if reminder:
                reminder["id"] = str(reminder["_id"])
                reminder.pop("_id", None)
            return reminder
        except Exception:
            return None

    def get_by_vehicle(self, vehicle_id: str, user_id: str):
        reminders = list(self.collection.find({
            "vehicle_id": vehicle_id,
            "user_id": user_id
        }))
        return [
            {**{k: v for k, v in r.items() if k != "_id"}, "id": str(r["_id"])} for r in reminders if "_id" in r
        ]

    def update(self, reminder_id: str, user_id: str, data: dict):
        try:
            if "due_by_date" in data and data["due_by_date"] and isinstance(data["due_by_date"], str):
                data["due_by_date"] = datetime.fromisoformat(data["due_by_date"])
            if "last_completed_date" in data and data["last_completed_date"] and isinstance(data["last_completed_date"], str):
                data["last_completed_date"] = datetime.fromisoformat(data["last_completed_date"])
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(reminder_id), "user_id": user_id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    def delete(self, reminder_id: str, user_id: str):
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(reminder_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False
