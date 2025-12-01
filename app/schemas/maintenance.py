from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MaintenanceCreate(BaseModel):
    date: str  # ISO format
    service_type: str
    description: Optional[str] = None
    mileage: int
    cost: Optional[float] = 0
    service_provider: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    date: Optional[str] = None
    service_type: Optional[str] = None
    description: Optional[str] = None
    mileage: Optional[int] = None
    cost: Optional[float] = None
    service_provider: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceResponse(BaseModel):
    id: str
    vehicle_id: str
    date: datetime
    service_type: str
    description: Optional[str] = None
    mileage: int
    cost: float
    service_provider: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
