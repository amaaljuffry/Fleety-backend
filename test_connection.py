import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# Apply SSL patch FIRST
sys.path.insert(0, os.path.dirname(__file__))
try:
    import ssl_patch  # noqa
    print("✅ SSL patch applied")
except Exception as e:
    print(f"⚠️ SSL patch failed: {e}")

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

print("Testing MongoDB Atlas connection with SSL...")
print(f"Connecting to: {MONGODB_URL[:50]}...")

try:
    client = MongoClient(
        MONGODB_URL,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        retryWrites=True
    )
    
    # Test ping
    result = client.admin.command('ping')
    print("✅ Connection successful!")
    print(f"Server info: {result}")
    
    # Test database access
    db = client["carlog"]
    print(f"✅ Database 'carlog' accessible")
    
    client.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"Error type: {type(e).__name__}")