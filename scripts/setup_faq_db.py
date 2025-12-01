#!/usr/bin/env python
"""
Database setup script for FAQ system
- Initializes FAQ collection
- Seeds sample FAQs
- Creates indexes
"""
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://petaiagency24_db_user:gDqv9EF5R9KrJQLK@cluster0.zcqdfln.mongodb.net/?appName=Cluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "Fleety_db")

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
        "question": "How do I reset my password?",
        "answer": "Click 'Forgot Password' on the login page, enter your email, and follow the instructions sent to your inbox."
    },
    {
        "question": "Is my data secure?",
        "answer": "Yes! We use 256-bit encryption, regular security audits, and comply with GDPR/PDPA standards. Your data is backed up daily."
    },
    {
        "question": "How do I generate a maintenance report?",
        "answer": "Go to 'Reports' > 'Maintenance', select your date range and vehicles, then click 'Generate Report'. You can view it online or download as PDF."
    },
    {
        "question": "Can I track fuel consumption per vehicle?",
        "answer": "Yes! In the 'Vehicles' section, click on any vehicle to see detailed fuel consumption history, trends, and cost analysis."
    },
    {
        "question": "How do I register an account?",
        "answer": "Click 'Sign Up' on the homepage, enter your email, create a password, and provide your company details. You'll receive a verification email to confirm your account."
    },
    {
        "question": "What's included in the Free Trial?",
        "answer": "The 14-day free trial includes full access to all features for up to 5 vehicles. No credit card required. Upgrade anytime to expand your fleet."
    },
]

def setup_faq_database():
    """
    Initialize FAQ database with sample questions
    """
    
    # Connect to MongoDB
    logger.info("🔗 Connecting to MongoDB...")
    try:
        client = MongoClient(
            MONGODB_URL,
            ssl=False,  # Disable SSL to workaround Windows TLS issue
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=False
        )
        db = client[DATABASE_NAME]
        collection = db["faqs"]
        logger.info(f"✅ Connected to {DATABASE_NAME}")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        return False

    # Clear existing FAQs (optional)
    logger.info("🧹 Clearing existing FAQs...")
    collection.delete_many({})

    # Insert FAQs
    logger.info("🚀 Setting up FAQ database...")

    inserted_count = 0
    failed_count = 0

    for faq in SAMPLE_FAQS:
        try:
            logger.info(f"📝 Processing: {faq['question'][:50]}...")

            # Insert FAQ without embedding (Gemini doesn't need it)
            result = collection.insert_one({
                "question": faq["question"],
                "answer": faq["answer"],
                "created_at": datetime.utcnow()
            })
            
            inserted_count += 1
            logger.info(f"✅ Inserted FAQ (ID: {result.inserted_id})")

        except Exception as e:
            failed_count += 1
            logger.error(f"❌ Error processing FAQ: {str(e)}")
            continue

    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Setup complete!")
    logger.info(f"   Inserted: {inserted_count} FAQs")
    logger.info(f"   Failed: {failed_count} FAQs")
    logger.info("=" * 60)

    # Create indexes
    logger.info("\n🔍 Creating indexes...")
    try:
        collection.create_index([("question", "text"), ("answer", "text")])
        logger.info("✅ Text index created")
    except Exception as e:
        logger.warning(f"⚠️ Index creation warning: {str(e)}")

    # Verify setup
    logger.info("\n📊 Verification:")
    faq_count = collection.count_documents({})
    logger.info(f"Total FAQs in database: {faq_count}")

    client.close()
    return True

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("FAQ Database Setup Script")
    logger.info("=" * 60)
    
    success = setup_faq_database()
    
    if success:
        logger.info("\n✅ FAQ database setup completed successfully!")
    else:
        logger.error("\n❌ FAQ database setup failed!")
        sys.exit(1)
