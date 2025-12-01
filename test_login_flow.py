#!/usr/bin/env python
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.user import User
from app.utils.auth import verify_password
from app.database import get_database
from pymongo import MongoClient

# Get database connection
client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']

# Create User model instance
user_model = User(db)

# Test login flow
email = "john@mail.com"
password = "password123"

print(f"Step 1: Finding user by email: {email}")
user = user_model.get_by_email(email)

print(f"Step 2: User found: {user is not None}")
if user:
    print(f"  User keys: {list(user.keys())}")
    print(f"  Email: {user.get('email')}")
    print(f"  ID: {user.get('id')}")
    print(f"  Hashed password exists: {user.get('hashed_password') is not None}")
    
    hash_val = user.get('hashed_password')
    if hash_val:
        print(f"  Hash type: {type(hash_val)}")
        print(f"  Hash: {hash_val}")
        
        print(f"\nStep 3: Verifying password...")
        result = verify_password(password, hash_val)
        print(f"  Result: {result}")
        
        if result:
            print(f"\nSUCCESS: Password verified!")
        else:
            print(f"\nFAILURE: Password verification failed!")
            
            # Try bcrypt directly
            import bcrypt
            print(f"\nDirect bcrypt test:")
            try:
                direct_result = bcrypt.checkpw(password.encode('utf-8'), hash_val.encode('utf-8'))
                print(f"  bcrypt.checkpw result: {direct_result}")
            except Exception as e:
                print(f"  bcrypt.checkpw error: {e}")
else:
    print(f"  User not found!")

client.close()
