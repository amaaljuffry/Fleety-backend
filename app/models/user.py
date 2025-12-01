from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime


class User:
    def __init__(self, db):
        self.collection: Collection = db["users"]
        # Create unique index on email
        self.collection.create_index("email", unique=True)

    def create(self, email: str, hashed_password: str, full_name: str = ""):
        user = {
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "preferences": {
                "email_notifications": True,
                "reminders_enabled": True,
                "theme": "light",
                "currency": "USD",
                "distance_unit": "miles"
            }
        }
        result = self.collection.insert_one(user)
        return {**user, "id": str(result.inserted_id)}

    def get_by_email(self, email: str):
        user = self.collection.find_one({"email": email})
        if user:
            user["id"] = str(user["_id"])
        return user

    def get_by_id(self, user_id: str):
        try:
            user = self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user["_id"])
            return user
        except Exception:
            return None

    def get_by_reset_token(self, token: str):
        """Get user by reset token"""
        user = self.collection.find_one({"reset_token": token})
        if user:
            user["id"] = str(user["_id"])
        return user

    def update(self, user_id: str, data: dict):
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)}, {"$set": data}
            )
            return result.modified_count > 0
        except Exception:
            return False
