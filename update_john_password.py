#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pymongo import MongoClient
from app.utils.auth import hash_password, verify_password

client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']

# Update john@mail.com password to admin123456
email = 'john@mail.com'
new_password = 'admin123456'

print(f"Updating {email} password to: {new_password}")
new_hash = hash_password(new_password)

result = db['users'].update_one(
    {'email': email},
    {'$set': {'hashed_password': new_hash}}
)

if result.modified_count > 0:
    print(f"✓ Password updated")
    
    # Verify
    user = db['users'].find_one({'email': email})
    hash_val = user.get('hashed_password')
    verify_result = verify_password(new_password, hash_val)
    print(f"✓ Verification result: {verify_result}")
else:
    print(f"✗ Failed to update password")

client.close()
