from datetime import datetime
from bson.objectid import ObjectId


class PublicContactInquiry:
    """Model for public contact inquiries from landing page"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.public_contact_inquiries
    
    def create(self, name: str, email: str, phone: str, subject: str, message: str, 
               agree_to_terms_and_privacy: bool, agree_to_pdpa: bool, 
               ip_address: str = None, user_agent: str = None):
        """Create a new public contact inquiry"""
        inquiry_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "message": message,
            "agreeToTermsAndPrivacy": agree_to_terms_and_privacy,
            "agreeToPDPA": agree_to_pdpa,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "status": "new",  # new, read, contacted, closed
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = self.collection.insert_one(inquiry_data)
        inquiry_data["_id"] = result.inserted_id
        return inquiry_data
    
    def get_all(self, skip: int = 0, limit: int = 50):
        """Get all inquiries (admin only)"""
        return list(self.collection.find().skip(skip).limit(limit))
    
    def get_by_id(self, inquiry_id: str):
        """Get inquiry by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(inquiry_id)})
        except:
            return None
    
    def get_by_email(self, email: str):
        """Get inquiries by email"""
        return list(self.collection.find({"email": email}))
    
    def update_status(self, inquiry_id: str, status: str):
        """Update inquiry status"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(inquiry_id)},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
            return result.modified_count > 0
        except:
            return False
    
    def mark_as_read(self, inquiry_id: str):
        """Mark inquiry as read by admin"""
        return self.update_status(inquiry_id, "read")
    
    def count_by_email(self, email: str, hours: int = 24):
        """Count inquiries from same email in last N hours"""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.collection.count_documents({
            "email": email,
            "created_at": {"$gte": cutoff_time}
        })
