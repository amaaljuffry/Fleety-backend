from fastapi import APIRouter, Depends, HTTPException, status, Header
from bson.errors import InvalidId
from app.models.driver import Driver
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse, DriverVehicleAssignment
from app.database import get_database
from app.utils.auth import decode_token
from typing import List

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


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


@router.post("", response_model=DriverResponse)
async def create_driver(
    driver_data: DriverCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Create a new driver"""
    driver_model = Driver(db)
    driver = driver_model.create(user_id, driver_data.dict())
    return driver


@router.get("", response_model=List[DriverResponse])
async def get_drivers(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get all drivers for the current user"""
    driver_model = Driver(db)
    drivers = driver_model.get_all_by_user(user_id)
    return drivers


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get a specific driver"""
    try:
        driver_model = Driver(db)
        driver = driver_model.get_by_id(driver_id, user_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        return driver
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid driver ID")


@router.put("/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: str,
    driver_data: DriverUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Update a driver"""
    try:
        driver_model = Driver(db)
        
        # Verify driver exists and belongs to user
        existing = driver_model.get_by_id(driver_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        # Update the driver
        update_data = driver_data.dict(exclude_unset=True)
        if driver_model.update(driver_id, user_id, update_data):
            updated = driver_model.get_by_id(driver_id, user_id)
            return updated
        else:
            raise HTTPException(status_code=400, detail="Failed to update driver")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid driver ID")


@router.post("/{driver_id}/assign-vehicle")
async def assign_vehicle(
    driver_id: str,
    assignment: DriverVehicleAssignment,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Assign a vehicle to a driver"""
    try:
        driver_model = Driver(db)
        
        # Verify driver exists and belongs to user
        existing = driver_model.get_by_id(driver_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        if driver_model.assign_vehicle(driver_id, user_id, assignment.vehicle_id):
            updated = driver_model.get_by_id(driver_id, user_id)
            return {"message": "Vehicle assigned successfully", "driver": updated}
        else:
            raise HTTPException(status_code=400, detail="Failed to assign vehicle")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid driver ID")


@router.post("/{driver_id}/unassign-vehicle")
async def unassign_vehicle(
    driver_id: str,
    assignment: DriverVehicleAssignment,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Unassign a vehicle from a driver"""
    try:
        driver_model = Driver(db)
        
        # Verify driver exists and belongs to user
        existing = driver_model.get_by_id(driver_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        if driver_model.unassign_vehicle(driver_id, user_id, assignment.vehicle_id):
            updated = driver_model.get_by_id(driver_id, user_id)
            return {"message": "Vehicle unassigned successfully", "driver": updated}
        else:
            raise HTTPException(status_code=400, detail="Failed to unassign vehicle")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid driver ID")


@router.get("/vehicle/{vehicle_id}", response_model=List[DriverResponse])
async def get_drivers_for_vehicle(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Get all drivers assigned to a specific vehicle"""
    driver_model = Driver(db)
    drivers = driver_model.get_by_vehicle(user_id, vehicle_id)
    return drivers


@router.delete("/{driver_id}")
async def delete_driver(
    driver_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    """Delete a driver"""
    try:
        driver_model = Driver(db)
        
        # Verify driver exists and belongs to user
        existing = driver_model.get_by_id(driver_id, user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        if driver_model.delete(driver_id, user_id):
            return {"message": "Driver deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete driver")
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid driver ID")
