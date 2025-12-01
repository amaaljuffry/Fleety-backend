#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.auth import verify_password
from pymongo import MongoClient
import bcrypt

# Get user's hash from database
client = MongoClient(os.getenv('MONGODB_URL'))
db = client['Fleety_db']
user = db['users'].find_one({'email': 'john@mail.com'})

if user:
    hash_val = user.get('hashed_password')
    print(f'Hash from DB: {hash_val}')
    print(f'Hash type: {type(hash_val)}')
    
    # Test with verify_password function
    result = verify_password('password123', hash_val)
    print(f'verify_password("password123", hash) result: {result}')
    
    # Also test with bcrypt directly
    try:
        bcrypt_result = bcrypt.checkpw(b'password123', hash_val.encode('utf-8'))
        print(f'bcrypt.checkpw(b"password123", hash.encode()) result: {bcrypt_result}')
    except Exception as e:
        print(f'bcrypt.checkpw error: {e}')
else:
    print('User not found')

client.close()
