from app.database import get_database
from typing import Dict, Any, Optional, List
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Waitlist:
    """
    Waitlist Model for storing early access signups
    
    Fields:
    - name: str (user's full name)
    - email: str (user's email address)
    - joined_at: datetime (when user joined)
    - status: str (pending, confirmed, converted)
    - source: str (where they came from: landing_page, social, etc.)
    - is_converted: bool (whether they became a paying customer)
    - converted_at: datetime (when they upgraded to paid)
    """

    collection_name = "waitlist"

    @classmethod
    def get_collection(cls):
        """Get MongoDB collection"""
        db = get_database()
        collection = db[cls.collection_name]
        # Create indexes
        collection.create_index("email", unique=True)
        collection.create_index("joined_at")
        collection.create_index("status")
        return collection

    @classmethod
    async def add_to_waitlist(
        cls,
        name: str,
        email: str,
        source: str = "landing_page"
    ) -> Dict[str, Any]:
        """
        Add a new user to the waitlist
        
        Args:
            name: User's full name
            email: User's email address
            source: Where they came from (landing_page, social, direct, etc.)
        
        Returns:
            Created document with ID
        
        Raises:
            ValueError: If email already exists in waitlist
        """
        try:
            collection = cls.get_collection()

            # Check if email already exists
            existing = collection.find_one({"email": email.lower()})
            if existing:
                logger.warning(f"Duplicate waitlist signup: {email}")
                raise ValueError("This email is already on the waitlist!")

            # Create document
            document = {
                "name": name.strip(),
                "email": email.lower().strip(),
                "source": source,
                "status": "pending",  # pending → confirmed → converted
                "is_converted": False,
                "joined_at": datetime.utcnow(),
                "converted_at": None,
                "notes": None
            }

            result = collection.insert_one(document)

            logger.info(f"Added to waitlist: {email} (ID: {str(result.inserted_id)})")

            return {
                "success": True,
                "id": str(result.inserted_id),
                "email": email,
                "message": "Successfully added to waitlist!"
            }

        except Exception as e:
            logger.error(f"Error adding to waitlist: {str(e)}")
            raise

    @classmethod
    async def mark_as_confirmed(cls, email: str) -> bool:
        """
        Mark waitlist entry as confirmed (email verified)
        
        Args:
            email: User's email address
        
        Returns:
            True if updated
        """
        try:
            collection = cls.get_collection()

            result = collection.update_one(
                {"email": email.lower()},
                {
                    "$set": {
                        "status": "confirmed",
                        "confirmed_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Marked as confirmed: {email}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error confirming waitlist entry: {str(e)}")
            return False

    @classmethod
    async def mark_as_converted(cls, email: str, user_id: str) -> bool:
        """
        Mark waitlist entry as converted (user became paying customer)
        
        Args:
            email: User's email address
            user_id: ID of created user account
        
        Returns:
            True if updated
        """
        try:
            collection = cls.get_collection()

            result = collection.update_one(
                {"email": email.lower()},
                {
                    "$set": {
                        "is_converted": True,
                        "status": "converted",
                        "converted_at": datetime.utcnow(),
                        "converted_user_id": user_id
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"Marked as converted: {email} → {user_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error converting waitlist entry: {str(e)}")
            return False

    @classmethod
    async def get_waitlist_stats(cls) -> Dict[str, Any]:
        """
        Get waitlist statistics
        
        Returns:
        {
            "total_signups": int,
            "confirmed": int,
            "converted": int,
            "pending": int,
            "conversion_rate": float,
            "by_source": {source: count, ...}
        }
        """
        try:
            collection = cls.get_collection()

            # Total counts
            total = collection.count_documents({})
            confirmed = collection.count_documents({"status": "confirmed"})
            converted = collection.count_documents({"is_converted": True})
            pending = collection.count_documents({"status": "pending"})

            # By source
            sources_pipeline = [
                {
                    "$group": {
                        "_id": "$source",
                        "count": {"$sum": 1}
                    }
                }
            ]
            sources_result = list(collection.aggregate(sources_pipeline))
            by_source = {item["_id"]: item["count"] for item in sources_result}

            # Conversion rate
            conversion_rate = (converted / total * 100) if total > 0 else 0

            return {
                "total_signups": total,
                "confirmed": confirmed,
                "converted": converted,
                "pending": pending,
                "conversion_rate": round(conversion_rate, 2),
                "by_source": by_source
            }

        except Exception as e:
            logger.error(f"Error getting waitlist stats: {str(e)}")
            return {
                "total_signups": 0,
                "confirmed": 0,
                "converted": 0,
                "pending": 0,
                "conversion_rate": 0,
                "by_source": {}
            }

    @classmethod
    async def get_all_waitlist(
        cls,
        limit: int = 100,
        skip: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all waitlist entries (admin only)
        
        Args:
            limit: Max records to return
            skip: Records to skip for pagination
            status_filter: Filter by status (pending, confirmed, converted)
        
        Returns:
            List of waitlist entries
        """
        try:
            collection = cls.get_collection()

            query = {}
            if status_filter:
                query["status"] = status_filter

            entries = collection.find(query).sort("joined_at", -1).skip(skip).limit(limit)

            result = []
            for entry in entries:
                entry["id"] = str(entry["_id"])
                result.append(entry)

            return result

        except Exception as e:
            logger.error(f"Error getting waitlist: {str(e)}")
            return []

    @classmethod
    async def send_bulk_email(
        cls,
        subject: str,
        content: str,
        status_filter: str = "confirmed"
    ) -> Dict[str, Any]:
        """
        Send bulk email to waitlist (for updates)
        Requires email service integration
        
        Args:
            subject: Email subject
            content: Email content/body
            status_filter: Only send to confirmed/converted users
        
        Returns:
            Send status
        """
        try:
            collection = cls.get_collection()

            # Get all confirmed/converted emails
            query = {
                "$or": [
                    {"status": "confirmed"},
                    {"status": "converted"}
                ]
            } if status_filter == "confirmed" else {}

            emails = collection.find(query).distinct("email")

            logger.info(f"Bulk email ready to {len(emails)} users")

            # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
            # send_email_service.send_bulk(emails, subject, content)

            return {
                "success": True,
                "recipients": len(emails),
                "message": "Bulk email queued"
            }

        except Exception as e:
            logger.error(f"Error sending bulk email: {str(e)}")
            return {
                "success": False,
                "recipients": 0,
                "error": str(e)
            }

    @classmethod
    async def export_waitlist(cls) -> List[Dict[str, Any]]:
        """
        Export all waitlist entries for download/analysis
        
        Returns:
            List of all waitlist entries
        """
        try:
            collection = cls.get_collection()
            entries = collection.find({}).sort("joined_at", -1)

            result = []
            for entry in entries:
                result.append({
                    "name": entry.get("name"),
                    "email": entry.get("email"),
                    "joined_at": entry.get("joined_at"),
                    "status": entry.get("status"),
                    "is_converted": entry.get("is_converted"),
                    "converted_at": entry.get("converted_at"),
                    "source": entry.get("source")
                })

            logger.info(f"Exported {len(result)} waitlist entries")
            return result

        except Exception as e:
            logger.error(f"Error exporting waitlist: {str(e)}")
            return []

    @classmethod
    async def unsubscribe(cls, email: str) -> bool:
        """
        Unsubscribe an email from the waitlist
        
        Args:
            email: Email address to unsubscribe
            
        Returns:
            bool: True if unsubscribed successfully
        """
        try:
            collection = cls.get_collection()
            email = email.lower().strip()
            
            result = await collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "subscribed": False,
                        "unsubscribed_at": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count > 0:
                logger.info(f"Email unsubscribed: {email}")
                return True
            else:
                logger.warning(f"Email not found for unsubscribe: {email}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing email {email}: {str(e)}")
            raise
