from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import List
from app.database import get_database
from app.models.reminder import Reminder
from app.models.vehicle import Vehicle
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderResponse
from app.utils.auth import decode_token

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


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


@router.get("/vehicle/{vehicle_id}", response_model=List[ReminderResponse])
async def get_reminders(
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
    
    reminder_model = Reminder(db)
    reminders = reminder_model.get_by_vehicle(vehicle_id, user_id)
    return reminders


@router.post("/vehicle/{vehicle_id}", response_model=ReminderResponse)
async def create_reminder(
    vehicle_id: str,
    reminder: ReminderCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    # Verify vehicle belongs to user
    vehicle_model = Vehicle(db)
    vehicle = vehicle_model.get_by_id(vehicle_id, user_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found (id: {vehicle_id})"
        )
    
    reminder_model = Reminder(db)
    created_reminder = reminder_model.create(user_id, vehicle_id, reminder.dict())
    return created_reminder


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    reminder_model = Reminder(db)
    reminder = reminder_model.get_by_id(reminder_id, user_id)
    
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    return reminder


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: str,
    reminder_update: ReminderUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    reminder_model = Reminder(db)
    
    # Check if reminder exists
    existing_reminder = reminder_model.get_by_id(reminder_id, user_id)
    if not existing_reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    # Update reminder
    update_data = {k: v for k, v in reminder_update.dict().items() if v is not None}
    success = reminder_model.update(reminder_id, user_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update reminder"
        )
    
    updated_reminder = reminder_model.get_by_id(reminder_id, user_id)
    return updated_reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database)
):
    reminder_model = Reminder(db)
    
    success = reminder_model.delete(reminder_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    return None
