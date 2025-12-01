from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReminderCreate(BaseModel):
    service_type: str
    description: Optional[str] = None
    due_by_mileage: Optional[int] = None
    due_by_date: Optional[str] = None  # ISO format
    reminder_threshold_miles: Optional[int] = 0
    reminder_threshold_days: Optional[int] = 0
    is_recurring: bool = False
    recurring_interval_miles: Optional[int] = None
    recurring_interval_months: Optional[int] = None
    last_completed_date: Optional[str] = None
    last_completed_mileage: Optional[int] = None


class ReminderUpdate(BaseModel):
    service_type: Optional[str] = None
    description: Optional[str] = None
    due_by_mileage: Optional[int] = None
    due_by_date: Optional[str] = None
    reminder_threshold_miles: Optional[int] = None
    reminder_threshold_days: Optional[int] = None
    is_recurring: Optional[bool] = None
    recurring_interval_miles: Optional[int] = None
    recurring_interval_months: Optional[int] = None
    last_completed_date: Optional[str] = None
    last_completed_mileage: Optional[int] = None
    is_active: Optional[bool] = None


class ReminderResponse(BaseModel):
    id: str
    service_type: str
    description: Optional[str] = None
    due_by_mileage: Optional[int] = None
    due_by_date: Optional[datetime] = None
    reminder_threshold_miles: int
    reminder_threshold_days: int
    is_recurring: bool
    recurring_interval_miles: Optional[int] = None
    recurring_interval_months: Optional[int] = None
    last_completed_date: Optional[datetime] = None
    last_completed_mileage: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
