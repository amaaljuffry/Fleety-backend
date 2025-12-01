#!/usr/bin/env python
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.auth import verify_password
from pymongo import MongoClient

client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']

user = db['users'].find_one({'email': 'john@mail.com'})
if user:
    print(f"User found: {user.get('email')}")
    hash_val = user.get('hashed_password')
    print(f"Hashed password: {hash_val}")
    print(f"Hash starts with: {hash_val[:10]}")
    
    # Test verification
    test_password = 'password123'
    result = verify_password(test_password, hash_val)
    print(f"Password '{test_password}' valid: {result}")
else:
    print("User not found")

client.close()
