from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from typing import List, Optional


class Document:
    """Model for vehicle documents (insurance, registration, inspection, receipts)"""
    
    DOCUMENT_TYPES = [
        "insurance",
        "registration", 
        "inspection",
        "service_receipt",
        "other"
    ]
    
    def __init__(self, db):
        self.collection: Collection = db["documents"]
        self.collection.create_index("vehicle_id")
        self.collection.create_index("user_id")

    def create(self, user_id: str, vehicle_id: str, document_data: dict):
        """Create a new document record"""
        document = {
            "user_id": user_id,
            "vehicle_id": vehicle_id,
            "document_type": document_data.get("document_type", "other"),
            "title": document_data.get("title"),
            "description": document_data.get("description"),
            "file_name": document_data.get("file_name"),
            "file_url": document_data.get("file_url"),
            "file_size": document_data.get("file_size", 0),
            "mime_type": document_data.get("mime_type"),
            "expiry_date": document_data.get("expiry_date"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(document)
        document["id"] = str(result.inserted_id)
        document.pop("_id", None)
        return document

    def get_by_id(self, document_id: str, user_id: str):
        """Get a document by ID"""
        try:
            document = self.collection.find_one({
                "_id": ObjectId(document_id),
                "user_id": user_id
            })
            if document:
                document["id"] = str(document["_id"])
                document.pop("_id", None)
            return document
        except Exception:
            return None

    def get_by_vehicle(self, vehicle_id: str, user_id: str) -> List[dict]:
        """Get all documents for a specific vehicle"""
        documents = list(self.collection.find({
            "vehicle_id": vehicle_id,
            "user_id": user_id
        }).sort("created_at", -1))
        
        result = []
        for doc in documents:
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc.pop("_id", None)
                result.append(doc)
        return result

    def get_all_by_user(self, user_id: str) -> List[dict]:
        """Get all documents for a user"""
        documents = list(self.collection.find({
            "user_id": user_id
        }).sort("created_at", -1))
        
        result = []
        for doc in documents:
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc.pop("_id", None)
                result.append(doc)
        return result

    def get_expiring_soon(self, user_id: str, days: int = 30) -> List[dict]:
        """Get documents expiring within specified days"""
        from datetime import timedelta
        expiry_threshold = datetime.utcnow() + timedelta(days=days)
        
        documents = list(self.collection.find({
            "user_id": user_id,
            "expiry_date": {
                "$ne": None,
                "$lte": expiry_threshold,
                "$gte": datetime.utcnow()
            }
        }).sort("expiry_date", 1))
        
        result = []
        for doc in documents:
            if "_id" in doc:
                doc["id"] = str(doc["_id"])
                doc.pop("_id", None)
                result.append(doc)
        return result

    def update(self, document_id: str, user_id: str, data: dict):
        """Update a document"""
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(document_id), "user_id": user_id},
                {"$set": data}
            )
            if result.modified_count > 0:
                return self.get_by_id(document_id, user_id)
            return None
        except Exception:
            return None

    def delete(self, document_id: str, user_id: str):
        """Delete a document"""
        try:
            result = self.collection.delete_one({
                "_id": ObjectId(document_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception:
            return False

    def delete_by_vehicle(self, vehicle_id: str, user_id: str):
        """Delete all documents for a vehicle"""
        try:
            result = self.collection.delete_many({
                "vehicle_id": vehicle_id,
                "user_id": user_id
            })
            return result.deleted_count
        except Exception:
            return 0
