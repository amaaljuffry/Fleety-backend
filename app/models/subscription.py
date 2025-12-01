"""
Subscription Model for Fleety Stripe Integration
Handles subscription storage and management in MongoDB
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from app.database import get_database

class SubscriptionBase(BaseModel):
    """Base subscription schema"""
    user_id: str
    plan_id: str  # 'starter', 'pro', 'enterprise'
    vehicle_count: int = Field(ge=1, le=500)
    stripe_customer_id: str
    stripe_subscription_id: str
    stripe_price_id: str
    status: str = "active"  # active, cancelled, past_due, trialing
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription"""
    user_id: str
    plan_id: str
    vehicle_count: int = Field(ge=1, le=500)
    stripe_customer_id: str
    stripe_subscription_id: str
    stripe_price_id: str
    status: str = "active"


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription"""
    plan_id: Optional[str] = None
    vehicle_count: Optional[int] = Field(default=None, ge=1, le=500)
    status: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    """Response schema for subscription"""
    id: str
    user_id: str
    plan_id: str
    vehicle_count: int
    stripe_customer_id: str
    stripe_subscription_id: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Subscription:
    """MongoDB Subscription Model - Synchronous"""
    collection_name = "subscriptions"

    @classmethod
    def get_collection(cls):
        """Get MongoDB collection (synchronous)"""
        db = get_database()
        return db[cls.collection_name]

    @classmethod
    def create(cls, subscription_data: SubscriptionCreate) -> dict:
        """Create a new subscription"""
        collection = cls.get_collection()
        
        data = subscription_data.model_dump()
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        data["current_period_start"] = None
        data["current_period_end"] = None
        data["cancel_at_period_end"] = False
        
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    @classmethod
    def find_by_user_id(cls, user_id: str) -> Optional[dict]:
        """Find subscription by user ID"""
        collection = cls.get_collection()
        return collection.find_one({"user_id": user_id})

    @classmethod
    def find_by_stripe_subscription_id(cls, stripe_subscription_id: str) -> Optional[dict]:
        """Find subscription by Stripe subscription ID"""
        collection = cls.get_collection()
        return collection.find_one({"stripe_subscription_id": stripe_subscription_id})

    @classmethod
    def find_by_stripe_customer_id(cls, stripe_customer_id: str) -> Optional[dict]:
        """Find subscription by Stripe customer ID"""
        collection = cls.get_collection()
        return collection.find_one({"stripe_customer_id": stripe_customer_id})

    @classmethod
    def update(cls, subscription_id: str, update_data: SubscriptionUpdate) -> Optional[dict]:
        """Update a subscription"""
        collection = cls.get_collection()
        
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = collection.find_one_and_update(
            {"_id": ObjectId(subscription_id)},
            {"$set": update_dict},
            return_document=True
        )
        return result

    @classmethod
    def update_by_stripe_subscription_id(
        cls, 
        stripe_subscription_id: str, 
        update_data: dict
    ) -> Optional[dict]:
        """Update subscription by Stripe subscription ID"""
        collection = cls.get_collection()
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = collection.find_one_and_update(
            {"stripe_subscription_id": stripe_subscription_id},
            {"$set": update_data},
            return_document=True
        )
        return result

    @classmethod
    def cancel(cls, subscription_id: str) -> Optional[dict]:
        """Cancel a subscription"""
        collection = cls.get_collection()
        
        result = collection.find_one_and_update(
            {"_id": ObjectId(subscription_id)},
            {"$set": {
                "status": "cancelled",
                "updated_at": datetime.utcnow()
            }},
            return_document=True
        )
        return result

    @classmethod
    def get_active_subscriptions(cls) -> List[dict]:
        """Get all active subscriptions"""
        collection = cls.get_collection()
        return list(collection.find({"status": "active"}))


# Enterprise Lead/Contact Model
class EnterpriseLeadBase(BaseModel):
    """Schema for enterprise sales leads"""
    name: str
    email: str
    company_name: str
    company_size: str  # '1-10', '11-50', '51-200', '201-500', '500+'
    fleet_size: int = Field(ge=1)
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EnterpriseLeadCreate(BaseModel):
    """Create enterprise lead"""
    name: str
    email: str
    company_name: str
    company_size: str
    fleet_size: int = Field(ge=1)
    message: Optional[str] = None


class EnterpriseLead:
    """MongoDB Enterprise Lead Model - Synchronous"""
    collection_name = "enterprise_leads"

    @classmethod
    def get_collection(cls):
        """Get MongoDB collection (synchronous)"""
        db = get_database()
        return db[cls.collection_name]

    @classmethod
    def create(cls, lead_data: EnterpriseLeadCreate) -> dict:
        """Create a new enterprise lead"""
        collection = cls.get_collection()
        
        data = lead_data.model_dump()
        data["created_at"] = datetime.utcnow()
        data["status"] = "new"
        
        result = collection.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    @classmethod
    def find_all(cls) -> List[dict]:
        """Get all enterprise leads"""
        collection = cls.get_collection()
        return list(collection.find().sort("created_at", -1))
