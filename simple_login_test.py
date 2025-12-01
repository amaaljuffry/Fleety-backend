#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing login...")
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "email": "john@mail.com",
        "password": "password123"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    print("Login SUCCESS!")
    token = response.json().get("access_token")
    print(f"Token: {token[:30]}..." if token else "No token")
else:
    print("Login FAILED!")
