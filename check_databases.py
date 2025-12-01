#!/usr/bin/env python
"""
Check what databases exist in MongoDB
"""
import sys
sys.path.insert(0, './backend')

from pymongo import MongoClient

# Connect to MongoDB
MONGODB_URL = "mongodb+srv://petaiagency24_db_user:gDqv9EF5R9KrJQLK@cluster0.zcqdfln.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGODB_URL)

print("Available databases in MongoDB:")
print("=" * 60)

databases = client.list_database_names()
for db_name in databases:
    db = client[db_name]
    collections = db.list_collection_names()
    print(f"\nDatabase: {db_name}")
    print(f"  Collections: {collections if collections else 'None'}")
    
    # If this database has a 'users' collection, show user count
    if 'users' in collections:
        user_count = db['users'].count_documents({})
        users = list(db['users'].find({}, {'email': 1, 'full_name': 1}))
        print(f"  Users: {user_count}")
        for user in users:
            print(f"    • {user.get('email')} - {user.get('full_name')}")

print("\n" + "=" * 60)
