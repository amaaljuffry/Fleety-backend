#!/usr/bin/env python
import sys
import os
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pymongo import MongoClient

client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']

# Hash the password
password = 'password123'
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

print(f"Old hash: $2b$12$fMBgdSGUALrTFsrsgS80HOXVU2eYBiyy.SMUM3lVa5aYJr8tkA2qm")
print(f"New hash: {hashed.decode()}")

# Update the user
result = db['users'].update_one(
    {'email': 'john@mail.com'},
    {'$set': {'hashed_password': hashed.decode()}}
)

print(f"Updated: {result.modified_count} user(s)")

# Verify
user = db['users'].find_one({'email': 'john@mail.com'})
print(f"User hash now: {user.get('hashed_password')}")

# Test verification
test_result = bcrypt.checkpw(password.encode('utf-8'), user.get('hashed_password').encode('utf-8'))
print(f"Verification test: {test_result}")

client.close()
