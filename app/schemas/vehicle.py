from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VehicleCreate(BaseModel):
    make: str
    model: str
    year: int
    color: Optional[str] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    current_mileage: Optional[int] = 0
    image_url: Optional[str] = None


class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    current_mileage: Optional[int] = None
    image_url: Optional[str] = None


class VehicleResponse(BaseModel):
    id: str = Field(alias="_id")
    make: str
    model: str
    year: int
    color: Optional[str] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    current_mileage: int
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
        by_alias = True
