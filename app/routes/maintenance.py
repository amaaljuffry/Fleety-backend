from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import List
from app.database import get_database
from app.models.maintenance import Maintenance
from app.models.vehicle import Vehicle
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate, MaintenanceResponse
from app.utils.auth import decode_token

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


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


@router.get("/vehicle/{vehicle_id}", response_model=List[MaintenanceResponse])
async def get_maintenance_records(
    vehicle_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    # Verify vehicle belongs to user
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    maintenance_model = Maintenance(db)
    records = maintenance_model.get_by_vehicle(vehicle_id, user_id)
    return records


@router.post("/vehicle/{vehicle_id}", response_model=MaintenanceResponse)
async def create_maintenance_record(
    vehicle_id: str,
    maintenance: MaintenanceCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    # Verify vehicle belongs to user
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not vehicle:
        # More detailed error for debugging
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found (id: {vehicle_id})"
        )
    
    maintenance_model = Maintenance(db)
    created_record = maintenance_model.create(user_id, vehicle_id, maintenance.dict())
    return created_record


@router.get("/{maintenance_id}", response_model=MaintenanceResponse)
async def get_maintenance_record(
    maintenance_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    maintenance_model = Maintenance(db)
    record = maintenance_model.get_by_id(maintenance_id, user_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found"
        )
    
    return record


@router.put("/{maintenance_id}", response_model=MaintenanceResponse)
async def update_maintenance_record(
    maintenance_id: str,
    maintenance_update: MaintenanceUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    maintenance_model = Maintenance(db)
    
    # Check if record exists
    existing_record = maintenance_model.get_by_id(maintenance_id, user_id)
    if not existing_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found"
        )
    
    # Update record
    update_data = {k: v for k, v in maintenance_update.dict().items() if v is not None}
    success = maintenance_model.update(maintenance_id, user_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update maintenance record"
        )
    
    updated_record = maintenance_model.get_by_id(maintenance_id, user_id)
    return updated_record


@router.delete("/{maintenance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_record(
    maintenance_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    maintenance_model = Maintenance(db)
    
    success = maintenance_model.delete(maintenance_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found"
        )
    
    return None
