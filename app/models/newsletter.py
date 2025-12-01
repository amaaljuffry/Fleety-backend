from datetime import datetime
from bson.objectid import ObjectId


class Newsletter:
    """Newsletter subscription model"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.newsletter_subscriptions
    
    def subscribe(self, email: str):
        """Subscribe an email to the newsletter"""
        # Check if email already exists
        existing = self.collection.find_one({"email": email})
        if existing:
            return {
                "_id": str(existing["_id"]),
                "email": existing["email"],
                "subscribed": existing["subscribed"],
                "created_at": existing["created_at"],
                "message": "Email already subscribed"
            }
        
        subscription_data = {
            "email": email,
            "subscribed": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(subscription_data)
        subscription_data["_id"] = str(result.inserted_id)
        return subscription_data
    
    def unsubscribe(self, email: str):
        """Unsubscribe an email from the newsletter"""
        result = self.collection.update_one(
            {"email": email},
            {"$set": {"subscribed": False, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            return None
        return {"email": email, "subscribed": False}
    
    def get_by_email(self, email: str):
        """Get subscription by email"""
        subscription = self.collection.find_one({"email": email})
        if subscription:
            subscription["_id"] = str(subscription["_id"])
        return subscription
    
    def get_all_active(self):
        """Get all active subscriptions"""
        subscriptions = list(self.collection.find({"subscribed": True}))
        for sub in subscriptions:
            sub["_id"] = str(sub["_id"])
        return subscriptions
    
    def delete(self, email: str):
        """Delete a subscription"""
        result = self.collection.delete_one({"email": email})
        return result.deleted_count > 0
