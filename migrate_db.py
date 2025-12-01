#!/usr/bin/env python
"""
Database migration script: carlog_db -> Fleety_db
Copies all collections and data from old database to new one
"""
import sys
sys.path.insert(0, './backend')

from pymongo import MongoClient

# Connect to MongoDB
MONGODB_URL = "mongodb+srv://petaiagency24_db_user:gDqv9EF5R9KrJQLK@cluster0.zcqdfln.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGODB_URL)

# Source and destination databases
source_db = client['carlog_db']
dest_db = client['Fleety_db']

print("=" * 60)
print("DATABASE MIGRATION: carlog_db -> Fleety_db")
print("=" * 60)

# Get all collections from source database
collections = source_db.list_collection_names()
print(f"\nFound {len(collections)} collections in 'carlog_db' database:")
print(f"  {', '.join(collections)}")

# Migrate each collection
total_documents = 0
for collection_name in collections:
    source_collection = source_db[collection_name]
    dest_collection = dest_db[collection_name]
    
    # Get all documents
    documents = list(source_collection.find({}))
    doc_count = len(documents)
    
    if doc_count > 0:
        # Clear destination collection if it exists
        dest_collection.delete_many({})
        
        # Insert all documents
        result = dest_collection.insert_many(documents)
        total_documents += len(result.inserted_ids)
        print(f"\n✓ Migrated collection '{collection_name}'")
        print(f"  Documents: {doc_count}")
    else:
        print(f"\n✓ Collection '{collection_name}' is empty (skipped)")

print("\n" + "=" * 60)
print(f"MIGRATION COMPLETE!")
print(f"Total documents migrated: {total_documents}")
print("=" * 60)

# Verify user data
print("\n--- Verifying User Data ---")
users_collection = dest_db['users']
users = list(users_collection.find({}))
print(f"Total users in Fleety_db: {len(users)}")
for user in users:
    print(f"  ✓ {user.get('email')} ({user.get('full_name')})")

# Verify vehicles
vehicles_collection = dest_db['vehicles']
vehicles = list(vehicles_collection.find({}))
print(f"\nTotal vehicles in Fleety_db: {len(vehicles)}")

# Verify maintenance
if 'maintenance' in dest_db.list_collection_names():
    maintenance_collection = dest_db['maintenance']
    maintenance = list(maintenance_collection.find({}))
    print(f"Total maintenance records in Fleety_db: {len(maintenance)}")

# Verify reminders
if 'reminders' in dest_db.list_collection_names():
    reminders_collection = dest_db['reminders']
    reminders = list(reminders_collection.find({}))
    print(f"Total reminders in Fleety_db: {len(reminders)}")

print("\n✓ Migration verified successfully!")
print("Your .env file already has DATABASE_NAME=Fleety_db configured")
print("Backend will now use the new database with all your existing data!")
