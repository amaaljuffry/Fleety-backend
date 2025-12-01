#!/usr/bin/env python
"""
Manual test to check if password change works correctly
"""
import sys
sys.path.insert(0, './backend')

from pymongo import MongoClient
from app.utils.auth import hash_password, verify_password

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['Fleety']
users_collection = db['users']

# Get first user
user = users_collection.find_one({})
if not user:
    print("No users found in database")
    sys.exit(1)

user_id = user['_id']
email = user.get('email')
old_password_hash = user.get('hashed_password')

print(f"Found user: {email}")
print(f"Current hashed password (first 50 chars): {old_password_hash[:50]}")

# Simulate password change
original_password = "oldpassword123"  # This is what was set during signup/login
new_password = "newpassword456"

print(f"\n--- Testing password change ---")
print(f"Original password (should work with current hash): {original_password}")
print(f"New password (to be set): {new_password}")

# Verify the old password hash works with test password
print(f"\nVerifying old hash with original password: {verify_password(original_password, old_password_hash)}")

# Create new hash for new password
new_password_hash = hash_password(new_password)
print(f"New password hash (first 50 chars): {new_password_hash[:50]}")

# Test if new hash verifies with new password
print(f"Verifying new hash with new password: {verify_password(new_password, new_password_hash)}")
print(f"Verifying new hash with original password: {verify_password(original_password, new_password_hash)}")

# Now update in database
print(f"\n--- Updating password in database ---")
result = users_collection.update_one(
    {"_id": user_id},
    {"$set": {"hashed_password": new_password_hash}}
)
print(f"Update result - matched: {result.matched_count}, modified: {result.modified_count}")

# Verify the update
updated_user = users_collection.find_one({"_id": user_id})
updated_hash = updated_user.get('hashed_password')
print(f"\nAfter update:")
print(f"Updated hash (first 50 chars): {updated_hash[:50]}")
print(f"Hashes are identical: {updated_hash == new_password_hash}")
print(f"Verify updated hash with new password: {verify_password(new_password, updated_hash)}")
print(f"Verify updated hash with original password: {verify_password(original_password, updated_hash)}")

print("\n✅ Password change simulation complete!")
