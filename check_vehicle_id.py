"""
Check if a specific vehicle ID exists in the database
"""
import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
load_dotenv('backend/.env')

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://petaiagency24_db_user:gDqv9EF5R9KrJQLK@cluster0.zcqdfln.mongodb.net/?retryWrites=true&w=majority")
DATABASE_NAME = os.getenv("DATABASE_NAME", "Fleety_db")

def check_vehicle(vehicle_id: str):
    """Check if vehicle exists and show its details"""
    print(f"\n{'='*60}")
    print(f"Checking Vehicle ID: {vehicle_id}")
    print(f"{'='*60}\n")
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = MongoClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        # Try to find the vehicle
        print(f"Searching in database: {DATABASE_NAME}")
        print(f"Collection: vehicles")
        
        # Convert string to ObjectId
        try:
            obj_id = ObjectId(vehicle_id)
            print(f"✅ Valid ObjectId format: {obj_id}\n")
        except Exception as e:
            print(f"❌ Invalid ObjectId format: {e}")
            return
        
        # Search by _id
        vehicle = db.vehicles.find_one({"_id": obj_id})
        
        if vehicle:
            print("✅ VEHICLE FOUND!")
            print(f"\n{'='*60}")
            print("Vehicle Details:")
            print(f"{'='*60}")
            for key, value in vehicle.items():
                if key == '_id':
                    print(f"  {key}: {value} (ObjectId)")
                else:
                    print(f"  {key}: {value}")
            print(f"{'='*60}\n")
            
            # Check user
            user_id = vehicle.get('user_id')
            if user_id:
                user = db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    print(f"Owner: {user.get('full_name')} ({user.get('email')})")
                else:
                    print(f"Owner ID: {user_id} (user not found)")
            
        else:
            print("❌ VEHICLE NOT FOUND")
            print("\nSearching all vehicles to see what exists...")
            
            # Show all vehicles
            all_vehicles = list(db.vehicles.find().limit(10))
            if all_vehicles:
                print(f"\nFound {len(all_vehicles)} vehicle(s) in database:")
                for v in all_vehicles:
                    print(f"  - ID: {v['_id']} | {v.get('year')} {v.get('make')} {v.get('model')}")
            else:
                print("\n⚠️  No vehicles found in database at all!")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # The vehicle ID to check
    vehicle_id = "6916867092f8a104974b04bd"
    check_vehicle(vehicle_id)
