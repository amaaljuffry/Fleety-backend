from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import List
from app.database import get_database
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from app.utils.auth import decode_token
from app.models.fuel_log import FuelLog
from app.schemas.fuel import FuelLogResponse, FuelLogCreate, FuelStatsResponse

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


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


@router.get("", response_model=List[VehicleResponse])
@router.get("/", response_model=List[VehicleResponse])
async def get_vehicles(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    vehicle_model = Vehicle(db)
    vehicles = vehicle_model.get_all_by_user(user_id)
    return vehicles


@router.post("", response_model=VehicleResponse)
@router.post("/", response_model=VehicleResponse)
async def create_vehicle(
    vehicle: VehicleCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    vehicle_model = Vehicle(db)
    created_vehicle = vehicle_model.create(user_id, vehicle.dict())
    return created_vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    vehicle_update: VehicleUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    vehicle_model = Vehicle(db)
    
    # Check if vehicle exists
    existing_vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Update vehicle
    update_data = {k: v for k, v in vehicle_update.dict().items() if v is not None}
    success = vehicle_model.update(vehicle_id, user_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update vehicle"
        )
    
    updated_vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    return updated_vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    vehicle_model = Vehicle(db)
    
    success = vehicle_model.delete(vehicle_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    return None


@router.get("/{vehicle_id}/fuel", response_model=List[FuelLogResponse])
async def get_vehicle_fuel_logs(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    fuel_model = FuelLog(db)
    logs = fuel_model.get_by_vehicle(user_id, vehicle_id)
    # Convert _id to id for Pydantic
    for log in logs:
        if '_id' in log:
            log['id'] = log['_id']
    return logs


@router.post("/{vehicle_id}/fuel", response_model=FuelLogResponse)
async def create_vehicle_fuel_log(
    vehicle_id: str,
    fuel_log: FuelLogCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    fuel_model = FuelLog(db)
    created_log = fuel_model.create(user_id, vehicle_id, fuel_log.dict())
    # Convert _id to id for Pydantic
    if '_id' in created_log:
        created_log['id'] = created_log['_id']
    return created_log


@router.get("/{vehicle_id}/fuel/stats", response_model=FuelStatsResponse)
async def get_vehicle_fuel_stats(
    vehicle_id: str,
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    fuel_model = FuelLog(db)
    stats = fuel_model.get_stats(user_id, vehicle_id, days)
    return stats
