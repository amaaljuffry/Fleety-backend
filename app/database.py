import os
import sys
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Apply SSL patch for Windows MongoDB Atlas
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    import ssl_patch  # noqa
except Exception as e:
    pass  # SSL patch is optional

logger = logging.getLogger(__name__)

# Get MongoDB URL from environment
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "Fleety_db")

client = None
db = None

# Lazy initialization - only connect when needed
def _connect_to_database():
    """Internal function to establish database connection"""
    global client, db
    
    if db is not None:
        return db  # Already connected
    
    # Try Atlas first
    try:
        logger.info(f"Attempting to connect to MongoDB: {MONGODB_URL[:50]}...")
        client = MongoClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            retryWrites=True
        )
        
        # Test connection
        client.admin.command("ping")
        logger.info("✅ MongoDB Atlas connected successfully")
        db = client[DB_NAME]
        return db
        
    except ServerSelectionTimeoutError as e:
        logger.warning(f"❌ MongoDB Atlas connection timeout: {e}")
        logger.info("Attempting local MongoDB fallback...")
        
        # Fallback to local MongoDB
        try:
            client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            logger.info("✅ Local MongoDB connected successfully")
            db = client[DB_NAME]
            return db
        except Exception as local_err:
            logger.error(f"❌ Local MongoDB also failed: {local_err}")
            logger.error("⚠️  MongoDB not available. Start MongoDB with: mongod")
            raise RuntimeError(
                "❌ Database not connected. Make sure MongoDB is running.\n"
                "   For local: run 'mongod' in a terminal\n"
                "   For Atlas: check MONGODB_URL in .env and IP whitelist"
            )
    
    except Exception as e:
        logger.error(f"❌ MongoDB general connection error: {e}")
        raise RuntimeError(
            "❌ Database not connected. Make sure MongoDB is running.\n"
            "   For local: run 'mongod' in a terminal\n"
            "   For Atlas: check MONGODB_URL in .env and IP whitelist"
        )

def get_database():
    """Return the database instance (lazy initialization)"""
    global db
    
    if db is None:
        _connect_to_database()
    
    return db

def close_database():
    """Close the MongoDB connection"""
    if client:
        client.close()
        logger.info("MongoDB connection closed")
