#!/usr/bin/env python3
"""
Test script to generate sample vehicle position data for testing the Live Tracking feature.
Run this script to populate the VehiclePositions collection with test data.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import random


BASE_URL = "http://localhost:8000"
TOKEN = None  # Will be set after login


def login(email: str = "john@mail.com", password: str = "password123"):
    """Login and get authentication token"""
    global TOKEN
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            TOKEN = data.get("access_token")
            print(f"✓ Logged in successfully")
            print(f"  Token: {TOKEN[:20]}...\n")
            return True
        else:
            print(f"✗ Login failed: {response.status_code}")
            print(f"  Response: {response.text}\n")
            return False
    except Exception as e:
        print(f"✗ Error logging in: {e}\n")
        return False


def get_vehicles() -> list:
    """Get list of vehicles from API"""
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/vehicles",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle both formats: direct array or wrapped in "vehicles" key
            if isinstance(data, list):
                vehicles = data
            else:
                vehicles = data.get("vehicles", [])
            
            print(f"✓ Retrieved {len(vehicles)} vehicles:")
            
            vehicle_list = []
            for v in vehicles:
                vehicle_id = v.get("_id") or v.get("id")
                vehicle_list.append({
                    "id": vehicle_id,
                    "make": v.get("make", "Unknown"),
                    "model": v.get("model", "Unknown"),
                    "lat": 40.7128 + random.uniform(-0.1, 0.1),
                    "lng": -74.006 + random.uniform(-0.1, 0.1),
                    "name": f"{v.get('make')} {v.get('model')}"
                })
                print(f"  - {vehicle_list[-1]['name']} (ID: {vehicle_id})")
            
            print()
            return vehicle_list
        else:
            print(f"✗ Failed to get vehicles: {response.status_code}")
            print(f"  Response: {response.text}\n")
            return []
    except Exception as e:
        print(f"✗ Error getting vehicles: {e}\n")
        return []


def generate_position_data(vehicle_id: str, base_lat: float, base_lng: float):
    """Generate random position data around a base location"""
    # Add some random variation to coordinates
    lat = base_lat + (random.random() - 0.5) * 0.05
    lng = base_lng + (random.random() - 0.5) * 0.05
    
    # Random speed between 0-80 km/h
    speed = random.uniform(0, 80)
    
    # Random direction 0-360 degrees
    direction = random.randint(0, 360)
    
    # Status based on speed
    status = "moving" if speed > 5 else "stopped"
    
    return {
        "latitude": lat,
        "longitude": lng,
        "speed": speed,
        "direction": direction,
        "status": status
    }


def test_position_update(vehicle_id: str, position_data: dict):
    """Test updating a vehicle position"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/vehicle-positions/{vehicle_id}",
            json=position_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✓ Updated position for vehicle {vehicle_id[:8]}...: {response.json()['status']}")
            return True
        else:
            print(f"✗ Failed to update vehicle {vehicle_id[:8]}...: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error updating vehicle {vehicle_id[:8]}...: {e}")
        return False


def test_get_latest_position(vehicle_id: str):
    """Test getting latest position for a vehicle"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/vehicle-positions/{vehicle_id}",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved latest position for vehicle {vehicle_id[:8]}...")
            print(f"  Speed: {data['position']['speed']:.2f} km/h")
            print(f"  Coordinates: {data['position']['location']['coordinates']}")
            return True
        else:
            print(f"✗ Failed to get position for vehicle {vehicle_id[:8]}...: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error getting position for vehicle {vehicle_id[:8]}...: {e}")
        return False


def test_get_all_latest_positions():
    """Test getting latest positions for all vehicles"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/vehicle-positions/latest/all",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved latest positions for all vehicles")
            print(f"  Total vehicles: {data['count']}")
            for pos in data['positions']:
                print(f"    - Vehicle {pos['vehicleId'][:8]}...: {pos['speed']:.2f} km/h")
            return True
        else:
            print(f"✗ Failed to get all positions: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error getting all positions: {e}")
        return False


def test_position_history(vehicle_id: str):
    """Test getting position history"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/vehicle-positions/{vehicle_id}/history?limit=10&hours_back=24",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Retrieved position history for vehicle {vehicle_id[:8]}...")
            print(f"  Total records: {data['count']}")
            return True
        else:
            print(f"✗ Failed to get history for vehicle {vehicle_id[:8]}...: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error getting history for vehicle {vehicle_id[:8]}...: {e}")
        return False


def run_continuous_simulation(vehicles: list, duration_seconds: int = 60, interval_seconds: int = 5):
    """Run a continuous simulation of vehicle movements"""
    if not vehicles:
        print("✗ No vehicles to simulate!")
        return
    
    print(f"\nStarting continuous simulation for {duration_seconds} seconds...")
    print(f"Updates every {interval_seconds} seconds\n")
    
    start_time = time.time()
    update_count = 0
    
    while time.time() - start_time < duration_seconds:
        for vehicle in vehicles:
            position_data = generate_position_data(
                vehicle["id"],
                vehicle["lat"],
                vehicle["lng"]
            )
            
            if test_position_update(vehicle["id"], position_data):
                update_count += 1
        
        # Display current state
        print(f"\nCurrent positions at {datetime.now().strftime('%H:%M:%S')}:")
        test_get_all_latest_positions()
        
        # Wait before next update
        elapsed = time.time() - start_time
        remaining = duration_seconds - elapsed
        
        if remaining > 0:
            print(f"\nWaiting {interval_seconds} seconds before next update... ({int(remaining)}s remaining)\n")
            time.sleep(interval_seconds)
    
    print(f"\nSimulation complete! Total updates: {update_count}")


def main():
    """Main test function"""
    print("=" * 60)
    print("Vehicle Position Tracking - Test Suite")
    print("=" * 60 + "\n")
    
    # Step 1: Login
    print("[STEP 1] Authenticating...")
    if not login():
        print("Cannot proceed without authentication.")
        return
    
    # Step 2: Get vehicles
    print("[STEP 2] Retrieving vehicles...")
    vehicles = get_vehicles()
    if not vehicles:
        print("Cannot proceed without vehicles.")
        return
    
    # Test 1: Update positions
    print("[TEST 1] Updating vehicle positions...")
    for vehicle in vehicles:
        position_data = generate_position_data(
            vehicle["id"],
            vehicle["lat"],
            vehicle["lng"]
        )
        test_position_update(vehicle["id"], position_data)
    
    time.sleep(1)
    
    # Test 2: Get latest positions
    print("\n[TEST 2] Retrieving latest positions...")
    for vehicle in vehicles:
        test_get_latest_position(vehicle["id"])
        time.sleep(0.5)
    
    # Test 3: Get all latest positions
    print("\n[TEST 3] Retrieving all latest positions...")
    test_get_all_latest_positions()
    
    # Test 4: Get position history
    print("\n[TEST 4] Retrieving position history...")
    for vehicle in vehicles:
        test_position_history(vehicle["id"])
        time.sleep(0.5)
    
    # Test 5: Continuous simulation
    print("\n[TEST 5] Running continuous simulation...")
    run_continuous_simulation(vehicles, duration_seconds=30, interval_seconds=5)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
