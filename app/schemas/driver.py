from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class DriverBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[str] = None
    is_primary: bool = False


class DriverCreate(DriverBase):
    assigned_vehicles: Optional[List[str]] = None


class DriverUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[str] = None
    is_primary: Optional[bool] = None
    assigned_vehicles: Optional[List[str]] = None


class DriverResponse(DriverBase):
    id: str
    assigned_vehicles: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DriverVehicleAssignment(BaseModel):
    driver_id: str
    vehicle_id: str
