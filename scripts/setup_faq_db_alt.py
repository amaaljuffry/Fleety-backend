#!/usr/bin/env python
"""
Alternative FAQ Database Setup - using app database configuration
"""
import sys
import os
import asyncio
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set env vars before importing
os.environ.setdefault("MONGODB_URL", "mongodb+srv://petaiagency24_db_user:gDqv9EF5R9KrJQLK@cluster0.zcqdfln.mongodb.net/?appName=Cluster0&retryWrites=false&ssl=false")
os.environ.setdefault("DATABASE_NAME", "Fleety_db")

from app.database import get_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample FAQs for Fleety
SAMPLE_FAQS = [
    {
        "question": "How do I add a new vehicle to my fleet?",
        "answer": "Navigate to the 'Vehicles' tab, click 'Add Vehicle', and fill in the vehicle details including registration number, make/model, and vehicle type. Click 'Save' to add it to your fleet."
    },
    {
        "question": "How do I track maintenance reminders?",
        "answer": "Go to 'Maintenance' > 'Reminders'. Set up automatic reminders based on mileage or date intervals. You'll receive notifications when maintenance is due."
    },
    {
        "question": "How do I view fuel costs and efficiency?",
        "answer": "In the 'Analytics' tab, select 'Fuel & Costs'. You can view fuel expenses per vehicle, efficiency trends, and compare performance across your fleet."
    },
    {
        "question": "Can I export maintenance records?",
        "answer": "Yes! Go to 'Maintenance' > 'Records', select the vehicles you want, and click 'Export'. You can export as PDF or CSV."
    },
    {
        "question": "How do I invite team members to manage the fleet?",
        "answer": "Go to 'Settings' > 'Team'. Click 'Invite Member', enter their email, and assign a role (Admin/Supervisor/Driver). They'll receive an invitation email."
    },
    {
        "question": "What payment methods do you accept?",
        "answer": "We accept credit cards (Visa, Mastercard, Amex), bank transfers, and digital wallets. Visit 'Settings' > 'Billing' to manage payment methods."
    },
    {
        "question": "Can I use Fleety with my existing ERP system?",
        "answer": "Yes, we offer API integration with most major ERP systems. Contact our support team at support@fleety.com for integration assistance."
    },
    {
        "question": "How do I generate fleet reports?",
        "answer": "Go to 'Reports' and select the report type (Maintenance, Fuel, Usage, Costs). Customize the date range and click 'Generate'. You can download as PDF or CSV."
    },
    {
        "question": "What is your data backup policy?",
        "answer": "Your fleet data is automatically backed up daily to secure cloud servers. In case of data loss, we can restore from the most recent backup within 24 hours."
    },
    {
        "question": "How do I set up driver compliance tracking?",
        "answer": "Navigate to 'Compliance' > 'Driver Licenses'. Add drivers and their license details. The system will send reminders when licenses are expiring soon."
    },
    {
        "question": "Can I track GPS location of my vehicles?",
        "answer": "Yes, with our GPS tracking feature. Go to 'Map View' to see real-time locations of all vehicles. This feature requires compatible GPS devices installed in your vehicles."
    },
    {
        "question": "Is there a free trial available?",
        "answer": "Yes! We offer a 14-day free trial with full access to all features. No credit card required. Sign up on our website to start your trial."
    },
]

def setup_faq_database():
    """Setup FAQ database with sample data"""
    try:
        logger.info("=" * 60)
        logger.info("FAQ Database Setup Script (Alternative)")
        logger.info("=" * 60)
        
        logger.info("🔗 Connecting to MongoDB...")
        db = get_database()
        collection = db["faqs"]
        logger.info(f"✅ Connected to database")
        
        # Test connection with a simple ping
        db.command('ping')
        logger.info("✅ Connection verified")
        
        # Clear existing FAQs
        logger.info("🧹 Clearing existing FAQs...")
        collection.delete_many({})
        
        # Insert FAQs
        logger.info("🚀 Inserting sample FAQs...")
        
        inserted_count = 0
        failed_count = 0
        
        for faq in SAMPLE_FAQS:
            try:
                logger.info(f"📝 Processing: {faq['question'][:50]}...")
                
                # Insert FAQ without embedding (Gemini doesn't need it)
                result = collection.insert_one({
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                logger.info(f"✅ Inserted with ID: {result.inserted_id}")
                inserted_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to insert FAQ: {str(e)}")
                failed_count += 1
        
        # Create indexes
        logger.info("📑 Creating indexes...")
        collection.create_index([("question", "text"), ("answer", "text")])
        logger.info("✅ Text indexes created")
        
        # Summary
        logger.info("=" * 60)
        logger.info(f"✅ FAQ database setup completed!")
        logger.info(f"📊 Stats:")
        logger.info(f"   - Inserted: {inserted_count} FAQs")
        logger.info(f"   - Failed: {failed_count} FAQs")
        logger.info(f"   - Total: {inserted_count + failed_count} FAQs")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_faq_database()
    sys.exit(0 if success else 1)
