from datetime import datetime
from bson.objectid import ObjectId


class Contact:
    """Contact model for support requests"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.contacts
    
    def create(self, name: str, email: str, phone: str, subject: str, message: str, 
               agree_to_terms_and_privacy: bool, agree_to_pdpa: bool, user_id: str = None):
        """Create a new contact/support request"""
        contact_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "message": message,
            "agreeToTermsAndPrivacy": agree_to_terms_and_privacy,
            "agreeToPDPA": agree_to_pdpa,
            "user_id": ObjectId(user_id) if user_id else None,
            "status": "open",  # open, in_progress, closed
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(contact_data)
        contact_data["_id"] = str(result.inserted_id)
        return contact_data
    
    def get_all(self, skip: int = 0, limit: int = 50):
        """Get all contact requests (admin only)"""
        return list(self.collection.find().skip(skip).limit(limit))
    
    def get_by_id(self, contact_id: str):
        """Get contact request by ID"""
        return self.collection.find_one({"_id": ObjectId(contact_id)})
    
    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 50):
        """Get contact requests by user"""
        return list(self.collection.find({"user_id": ObjectId(user_id)}).skip(skip).limit(limit))
    
    def update_status(self, contact_id: str, status: str):
        """Update contact request status"""
        result = self.collection.update_one(
            {"_id": ObjectId(contact_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result.modified_count > 0
    
    def add_reply(self, contact_id: str, reply_message: str, admin_id: str = None):
        """Add a reply to a contact request"""
        result = self.collection.update_one(
            {"_id": ObjectId(contact_id)},
            {
                "$push": {
                    "replies": {
                        "message": reply_message,
                        "admin_id": ObjectId(admin_id) if admin_id else None,
                        "created_at": datetime.utcnow(),
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result.modified_count > 0
