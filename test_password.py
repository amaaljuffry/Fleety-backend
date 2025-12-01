#!/usr/bin/env python
import sys
sys.path.insert(0, './backend')
from pymongo import MongoClient
from app.utils.auth import hash_password, verify_password

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['Fleety']
users_collection = db['users']

# Get all users
users = list(users_collection.find({}))

print(f"\nFound {len(users)} user(s) in database:")
for user in users:
    email = user.get('email', 'N/A')
    hashed = user.get('hashed_password', '')
    print(f"\nEmail: {email}")
    print(f"Hashed Password length: {len(hashed)}")
    print(f"Hashed Password (first 50 chars): {hashed[:50]}")

# Test hashing
print("\n\n--- Testing password hashing ---")
test_password = "newpassword123"
hashed1 = hash_password(test_password)
hashed2 = hash_password(test_password)

print(f"\nOriginal password: {test_password}")
print(f"Hash 1: {hashed1}")
print(f"Hash 2: {hashed2}")
print(f"Are hashes equal? {hashed1 == hashed2}")
print(f"Verify with hash 1: {verify_password(test_password, hashed1)}")
print(f"Verify with hash 2: {verify_password(test_password, hashed2)}")
