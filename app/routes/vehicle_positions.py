from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_database
from app.models.vehicle_position import VehiclePosition
from datetime import datetime, timezone

router = APIRouter(prefix="/api/vehicle-positions", tags=["vehicle-positions"])


# Pydantic schemas
class PositionUpdate(BaseModel):
    """Schema for updating vehicle position"""
    latitude: float
    longitude: float
    speed: float = 0
    direction: int = 0
    status: str = "active"  # moving, stopped, offline


class PositionResponse(BaseModel):
    """Schema for position response"""
    vehicleId: str
    location: dict
    speed: float
    direction: int
    status: str
    timestamp: datetime


# ============================================================================
# IMPORTANT: Specific routes MUST come before generic routes!
# Routes are matched in order, so /latest/all must come before /{vehicle_id}
# ============================================================================

@router.get("/latest/all")
async def get_all_latest_positions(db=Depends(get_database)):
    """
    Get latest positions for all vehicles
    
    Returns:
        List of latest position documents for all vehicles
    """
    try:
        position_model = VehiclePosition(db)
        positions = position_model.get_all_latest_positions()
        
        return {
            "status": "success",
            "count": len(positions),
            "positions": [
                {
                    "vehicleId": str(p.get("vehicleId")),
                    "location": p.get("location"),
                    "speed": p.get("speed"),
                    "direction": p.get("direction"),
                    "status": p.get("status"),
                    "timestamp": p.get("timestamp")
                }
                for p in positions
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving positions: {str(e)}"
        )


@router.get("/nearby/search")
async def find_vehicles_nearby(
    longitude: float = Query(..., description="Search center longitude"),
    latitude: float = Query(..., description="Search center latitude"),
    max_distance_km: float = Query(5, ge=0.1, le=100, description="Search radius in km"),
    db=Depends(get_database)
):
    """
    Find vehicles near a location using geospatial search
    
    Args:
        longitude: Search center longitude
        latitude: Search center latitude
        max_distance_km: Search radius in kilometers
    
    Returns:
        List of vehicles near the location
    """
    try:
        max_distance_meters = int(max_distance_km * 1000)
        position_model = VehiclePosition(db)
        positions = position_model.find_vehicles_near_location(
            longitude=longitude,
            latitude=latitude,
            max_distance_meters=max_distance_meters
        )
        
        return {
            "status": "success",
            "count": len(positions),
            "search_center": {
                "longitude": longitude,
                "latitude": latitude
            },
            "radius_km": max_distance_km,
            "vehicles": [
                {
                    "vehicleId": str(p.get("vehicleId")),
                    "location": p.get("location"),
                    "speed": p.get("speed"),
                    "direction": p.get("direction"),
                    "status": p.get("status"),
                    "timestamp": p.get("timestamp")
                }
                for p in positions
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in geospatial search: {str(e)}"
        )


@router.get("/{vehicle_id}/history")
async def get_vehicle_position_history(
    vehicle_id: str,
    limit: int = Query(100, ge=1, le=1000),
    hours_back: int = Query(24, ge=1, le=720),
    db=Depends(get_database)
):
    """
    Get historical positions for a vehicle
    
    Args:
        vehicle_id: MongoDB ObjectId of vehicle
        limit: Maximum number of positions (1-1000)
        hours_back: How many hours of history to retrieve (1-720 = 30 days)
    
    Returns:
        List of historical position documents
    """
    try:
        position_model = VehiclePosition(db)
        positions = position_model.get_position_history(
            vehicle_id=vehicle_id,
            limit=limit,
            hours_back=hours_back
        )
        
        return {
            "status": "success",
            "count": len(positions),
            "vehicle_id": vehicle_id,
            "query": {
                "limit": limit,
                "hours_back": hours_back
            },
            "positions": [
                {
                    "vehicleId": str(p.get("vehicleId")),
                    "location": p.get("location"),
                    "speed": p.get("speed"),
                    "direction": p.get("direction"),
                    "status": p.get("status"),
                    "timestamp": p.get("timestamp")
                }
                for p in positions
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving history: {str(e)}"
        )


# ============================================================================
# Generic routes - MUST come last!
# ============================================================================

@router.post("/{vehicle_id}")
async def update_vehicle_position(
    vehicle_id: str,
    position_data: PositionUpdate,
    db=Depends(get_database)
):
    """
    Update vehicle position (called by GPS/IoT device or mobile app)
    
    Args:
        vehicle_id: MongoDB ObjectId of vehicle (from /api/vehicles/{id})
        position_data: Position update data (lat, lng, speed, direction, status)
    
    Returns:
        Created position document
    """
    try:
        position_model = VehiclePosition(db)
        
        result = position_model.create_position(
            vehicle_id=vehicle_id,
            latitude=position_data.latitude,
            longitude=position_data.longitude,
            speed=position_data.speed,
            direction=position_data.direction,
            status=position_data.status
        )
        
        if result:
            return {
                "status": "success",
                "message": "Position updated",
                "position": {
                    "vehicleId": str(result.get("vehicleId")),
                    "location": result.get("location"),
                    "speed": result.get("speed"),
                    "direction": result.get("direction"),
                    "status": result.get("status"),
                    "timestamp": result.get("timestamp")
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update position"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating position: {str(e)}"
        )


@router.get("/{vehicle_id}")
async def get_vehicle_latest_position(
    vehicle_id: str,
    db=Depends(get_database)
):
    """
    Get latest position for a specific vehicle
    
    Args:
        vehicle_id: MongoDB ObjectId of vehicle (from /api/vehicles/{id})
    
    Returns:
        Latest position document
    """
    try:
        position_model = VehiclePosition(db)
        position = position_model.get_latest_position(vehicle_id)
        
        if position:
            return {
                "status": "success",
                "position": {
                    "vehicleId": str(position.get("vehicleId")),
                    "location": position.get("location"),
                    "speed": position.get("speed"),
                    "direction": position.get("direction"),
                    "status": position.get("status"),
                    "timestamp": position.get("timestamp")
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No position data found for this vehicle"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving position: {str(e)}"
        )

