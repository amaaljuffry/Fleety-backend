#!/usr/bin/env python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Connect to MongoDB  
uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
print(f"Connecting to: {uri[:60]}...")

client = MongoClient(uri, serverSelectionTimeoutMS=5000)

try:
    db = client["Fleety_db"]
    
    # Check users
    print("\n=== USERS IN DATABASE ===")
    users = list(db["users"].find())
    if users:
        for user in users:
            email = user.get('email')
            uid = user.get('_id')
            hash_val = user.get('hashed_password')
            print(f"Email: {email}, ID: {uid}")
            if hash_val:
                print(f"  Hash: {hash_val}")
    else:
        print("No users found")
    
    # Check vehicles
    print("\n=== VEHICLES IN DATABASE ===")
    vehicles = list(db["vehicles"].find())
    print(f"Total vehicles: {len(vehicles)}")
    for v in vehicles:
        print(f"  Make/Model: {v.get('make')} {v.get('model')}, User: {v.get('user_id')}, ID: {v.get('_id')}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
