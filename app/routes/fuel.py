from fastapi import APIRouter, Depends, HTTPException, status, Header
from bson.errors import InvalidId
from app.models.fuel_log import FuelLog
from app.models.vehicle import Vehicle
from app.schemas.fuel import FuelLogCreate, FuelLogUpdate, FuelLogResponse, FuelStatsResponse
from app.database import get_database
from app.utils.auth import decode_token
from typing import List

router = APIRouter(prefix="/api/fuel", tags=["fuel"])


def get_current_user_id(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return payload.get("sub")


@router.post("/vehicle/{vehicle_id}", response_model=FuelLogResponse)
async def create_fuel_log(
    vehicle_id: str,
    fuel_log: FuelLogCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Create a new fuel log entry"""
    try:
        # Verify vehicle exists and belongs to user
        vehicle_model = Vehicle(db)
        vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        fuel_model = FuelLog(db)
        fuel = fuel_model.create(user_id, vehicle_id, fuel_log.dict())
        if '_id' in fuel:
            fuel['id'] = fuel['_id']
        return fuel
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vehicle ID")


@router.get("/vehicle/{vehicle_id}", response_model=List[FuelLogResponse])
async def get_fuel_logs(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get all fuel logs for a vehicle"""
    try:
        # Verify vehicle exists and belongs to user
        vehicle_model = Vehicle(db)
        vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        fuel_model = FuelLog(db)
        logs = fuel_model.get_by_vehicle(user_id, vehicle_id)
        for log in logs:
            if '_id' in log:
                log['id'] = log['_id']
        return logs
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vehicle ID")


@router.get("/vehicle/{vehicle_id}/stats", response_model=FuelStatsResponse)
async def get_fuel_stats(
    vehicle_id: str,
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get fuel economy statistics for a vehicle"""
    try:
        # Verify vehicle exists and belongs to user
        vehicle_model = Vehicle(db)
        vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        fuel_model = FuelLog(db)
        stats = fuel_model.get_stats(user_id, vehicle_id, days)
        return stats
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vehicle ID")


@router.get("/{fuel_log_id}", response_model=FuelLogResponse)
async def get_fuel_log(
    fuel_log_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get a specific fuel log"""
    try:
        fuel_model = FuelLog(db)
        fuel = fuel_model.get_by_id(fuel_log_id, user_id)
        if not fuel:
            raise HTTPException(status_code=404, detail="Fuel log not found")
        if '_id' in fuel:
            fuel['id'] = fuel['_id']
        return fuel
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid fuel log ID")


@router.put("/{fuel_log_id}", response_model=FuelLogResponse)
async def update_fuel_log(
    fuel_log_id: str,
    fuel_log: FuelLogUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Update a fuel log"""
    try:
        fuel_model = FuelLog(db)
        
        # Verify fuel log exists and belongs to user
        existing = fuel_model.get_by_id(fuel_log_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Fuel log not found")
        
        # Update the fuel log
        update_data = fuel_log.dict(exclude_unset=True)
        if fuel_model.update(fuel_log_id, user_id, update_data):
            updated = fuel_model.get_by_id(fuel_log_id, user_id)
            if '_id' in updated:
                updated['id'] = updated['_id']
            return updated
        else:
            raise HTTPException(status_code=400, detail="Failed to update fuel log")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid fuel log ID")


@router.delete("/{fuel_log_id}")
async def delete_fuel_log(
    fuel_log_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Delete a fuel log"""
    try:
        fuel_model = FuelLog(db)
        
        # Verify fuel log exists and belongs to user
        existing = fuel_model.get_by_id(fuel_log_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Fuel log not found")
        
        if fuel_model.delete(fuel_log_id, user_id):
            return {"message": "Fuel log deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete fuel log")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid fuel log ID")
