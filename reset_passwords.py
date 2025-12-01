#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pymongo import MongoClient
from app.utils.auth import hash_password

client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']

# Create new PBKDF2 hashes for users
users_to_update = [
    ('john@mail.com', 'password123'),
    ('jane@mail.com', 'password123'),
    ('jorry@mail.com', 'password123'),
    ('user@example.com', 'password123'),
    ('petai@mail.com', 'password123'),
]

print("Updating passwords to PBKDF2 format...")
for email, password in users_to_update:
    new_hash = hash_password(password)
    result = db['users'].update_one(
        {'email': email},
        {'$set': {'hashed_password': new_hash}}
    )
    if result.modified_count > 0:
        print(f"✓ Updated {email}")
        print(f"  New hash: {new_hash[:40]}...")
    else:
        print(f"✗ Failed to update {email}")

print("\nVerifying passwords...")
from app.utils.auth import verify_password

for email, password in users_to_update:
    user = db['users'].find_one({'email': email})
    if user:
        hash_val = user.get('hashed_password')
        result = verify_password(password, hash_val)
        status = "✓" if result else "✗"
        print(f"{status} {email}: {result}")

client.close()
print("\nDone!")
