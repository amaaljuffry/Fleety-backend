from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime


class FuelLogCreate(BaseModel):
    # Vehicle & Odometer
    odometer_reading: float = Field(..., gt=0, description="Odometer reading at fill-up in km")
    
    # Fueling Details
    fuel_type: str = Field(..., description="Type of fuel (Diesel, Petrol RON95, RON97, RON92, Other)")
    liters: float = Field(..., gt=0, description="Amount of fuel added in liters")
    price_per_liter: Optional[float] = Field(None, ge=0, description="Price per liter of fuel in MYR")
    total_cost: float = Field(..., gt=0, description="Total price paid in MYR")
    fuel_station_name: Optional[str] = Field(None, description="Name of fuel station")
    
    # Driver & Operational
    driver_id: Optional[str] = None
    driver_notes: Optional[str] = None
    trip_purpose: Optional[str] = Field(None, description="Trip purpose (Business, Personal, Delivery, Other)")
    
    # Date & Time
    date: str = Field(..., description="Date of fueling in YYYY-MM-DD format")
    time: Optional[str] = Field(None, description="Time of fueling in HH:MM format")
    
    # Evidence & Documentation
    receipt_url: Optional[str] = None
    pump_meter_photo_url: Optional[str] = None
    
    notes: Optional[str] = None


class FuelLogUpdate(BaseModel):
    # Vehicle & Odometer
    odometer_reading: Optional[float] = None
    
    # Fueling Details
    fuel_type: Optional[str] = None
    liters: Optional[float] = None
    price_per_liter: Optional[float] = None
    total_cost: Optional[float] = None
    fuel_station_name: Optional[str] = None
    
    # Driver & Operational
    driver_id: Optional[str] = None
    driver_notes: Optional[str] = None
    trip_purpose: Optional[str] = None
    
    # Date & Time
    date: Optional[str] = None
    time: Optional[str] = None
    
    # Evidence & Documentation
    receipt_url: Optional[str] = None
    pump_meter_photo_url: Optional[str] = None
    
    notes: Optional[str] = None


class FuelLogResponse(BaseModel):
    id: str = Field(serialization_alias="_id")
    vehicle_id: str
    
    # Vehicle & Odometer
    odometer_reading: Optional[float] = None
    
    # Fueling Details
    fuel_type: Optional[str] = None
    liters: Optional[float] = None
    price_per_liter: Optional[float] = None
    total_cost: Optional[float] = None
    fuel_station_name: Optional[str] = None
    
    # Driver & Operational
    driver_id: Optional[str] = None
    driver_notes: Optional[str] = None
    trip_purpose: Optional[str] = None
    
    # Date & Time
    date: Optional[str] = None
    time: Optional[str] = None
    
    # Evidence & Documentation
    receipt_url: Optional[str] = None
    pump_meter_photo_url: Optional[str] = None
    
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class FuelStatsResponse(BaseModel):
    average_mpg: Optional[float] = None
    total_cost: float
    total_fuel: float
    total_distance: float
    logs_count: int
    fuel_type: Optional[str] = None
