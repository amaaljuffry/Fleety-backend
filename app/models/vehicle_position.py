from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.database import get_database


class VehiclePosition:
    """Model for managing vehicle position tracking data"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db["VehiclePositions"]
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes for performance"""
        try:
            # Geospatial index for location-based queries
            self.collection.create_index([("location", "2dsphere")])
            # Index for latest position lookup
            self.collection.create_index([("vehicleId", 1), ("timestamp", -1)])
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    def create_position(
        self,
        vehicle_id: str,
        latitude: float,
        longitude: float,
        speed: float = 0,
        direction: int = 0,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create or update a vehicle position record
        
        Args:
            vehicle_id: MongoDB ObjectId of vehicle
            latitude: Vehicle latitude
            longitude: Vehicle longitude
            speed: Current speed in km/h
            direction: Direction in degrees (0-360)
            status: Vehicle status (moving, stopped, offline)
        
        Returns:
            Created position document
        """
        try:
            vehicle_oid = ObjectId(vehicle_id) if isinstance(vehicle_id, str) else vehicle_id
            
            position_doc = {
                "vehicleId": vehicle_oid,
                "location": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]  # GeoJSON format: [lon, lat]
                },
                "speed": speed,
                "direction": direction,
                "status": status,
                "timestamp": datetime.now(timezone.utc)
            }
            
            result = self.collection.insert_one(position_doc)
            position_doc["_id"] = result.inserted_id
            return position_doc
        except Exception as e:
            print(f"Error creating position: {e}")
            return None
    
    def get_latest_position(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest position for a specific vehicle
        
        Args:
            vehicle_id: MongoDB ObjectId of vehicle
        
        Returns:
            Latest position document or None
        """
        try:
            vehicle_oid = ObjectId(vehicle_id) if isinstance(vehicle_id, str) else vehicle_id
            
            position = self.collection.find_one(
                {"vehicleId": vehicle_oid},
                sort=[("timestamp", -1)]
            )
            return position
        except Exception as e:
            print(f"Error getting latest position: {e}")
            return None
    
    def get_all_latest_positions(self) -> List[Dict[str, Any]]:
        """
        Get latest positions for all vehicles
        
        Returns:
            List of latest position documents
        """
        try:
            # Pipeline to get latest position for each vehicle
            pipeline = [
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": "$vehicleId",
                        "position": {"$first": "$$ROOT"}
                    }
                },
                {"$replaceRoot": {"newRoot": "$position"}}
            ]
            
            positions = list(self.collection.aggregate(pipeline))
            return positions
        except Exception as e:
            print(f"Error getting all latest positions: {e}")
            return []
    
    def get_position_history(
        self,
        vehicle_id: str,
        limit: int = 100,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get historical positions for a vehicle
        
        Args:
            vehicle_id: MongoDB ObjectId of vehicle
            limit: Maximum number of positions to return
            hours_back: How many hours of history to retrieve
        
        Returns:
            List of position documents in chronological order
        """
        try:
            from datetime import timedelta
            
            vehicle_oid = ObjectId(vehicle_id) if isinstance(vehicle_id, str) else vehicle_id
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            positions = list(
                self.collection.find(
                    {
                        "vehicleId": vehicle_oid,
                        "timestamp": {"$gte": start_time}
                    },
                    sort=[("timestamp", 1)]
                ).limit(limit)
            )
            return positions
        except Exception as e:
            print(f"Error getting position history: {e}")
            return []
    
    def find_vehicles_near_location(
        self,
        longitude: float,
        latitude: float,
        max_distance_meters: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        Find vehicles near a specific location using geospatial query
        
        Args:
            longitude: Query longitude
            latitude: Query latitude
            max_distance_meters: Search radius in meters
        
        Returns:
            List of positions for vehicles within distance
        """
        try:
            pipeline = [
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": "$vehicleId",
                        "position": {"$first": "$$ROOT"}
                    }
                },
                {
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": [longitude, latitude]
                        },
                        "distanceField": "distance",
                        "maxDistance": max_distance_meters,
                        "spherical": True
                    }
                },
                {"$replaceRoot": {"newRoot": "$position"}}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception as e:
            print(f"Error in geospatial query: {e}")
            return []
    
    def delete_old_positions(self, days_to_keep: int = 30) -> int:
        """
        Clean up old position records (data retention)
        
        Args:
            days_to_keep: Keep positions from last N days
        
        Returns:
            Number of documents deleted
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            result = self.collection.delete_many({"timestamp": {"$lt": cutoff_date}})
            return result.deleted_count
        except Exception as e:
            print(f"Error deleting old positions: {e}")
            return 0
