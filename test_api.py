#!/usr/bin/env python
"""
Test script to create a user and verify settings endpoint
"""
import sys
import json
import requests
sys.path.insert(0, './backend')

from pymongo import MongoClient
from app.utils.auth import hash_password

# MongoDB connection
client = MongoClient('mongodb://localhost:27017')
db = client['Fleety']
users_collection = db['users']

# Clear existing test user
users_collection.delete_one({"email": "john@mail.com"})

# Create test user
test_user = {
    "email": "john@mail.com",
    "full_name": "John Doe",
    "hashed_password": hash_password("password123"),
    "is_active": True,
    "preferences": {
        "distance_unit": "km",
        "currency": "USD",
        "email_notifications": True,
        "reminders_enabled": True,
        "theme": "light"
    }
}

result = users_collection.insert_one(test_user)
print(f"✓ Created test user: john@mail.com")
print(f"  User ID: {result.inserted_id}")

# Test login
print("\n--- Testing Login ---")
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "john@mail.com", "password": "password123"}
)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    login_data = login_response.json()
    token = login_data.get("access_token")
    print(f"✓ Login successful")
    print(f"  Token: {token[:20]}...")
    
    # Test settings endpoint
    print("\n--- Testing Settings Endpoint ---")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    settings_response = requests.get(
        "http://localhost:8000/api/settings/preferences",
        headers=headers
    )
    print(f"Settings status: {settings_response.status_code}")
    
    if settings_response.status_code == 200:
        settings_data = settings_response.json()
        print(f"✓ Settings retrieved successfully")
        print(f"  Distance unit: {settings_data.get('distance_unit')}")
        print(f"  Currency: {settings_data.get('currency')}")
        print(f"  Theme: {settings_data.get('theme')}")
    else:
        print(f"✗ Settings endpoint failed: {settings_response.text}")
else:
    print(f"✗ Login failed: {login_response.text}")

print("\n--- All tests completed ---")
