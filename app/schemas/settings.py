from pydantic import BaseModel
from typing import Literal


class PreferencesUpdate(BaseModel):
    email_notifications: bool = None
    reminders_enabled: bool = None
    theme: Literal["light", "dark", "auto"] = None
    currency: Literal["USD", "EUR", "GBP", "CAD", "AUD", "RM"] = None
    distance_unit: Literal["miles", "km"] = None

    class Config:
        from_attributes = True


class PreferencesResponse(BaseModel):
    email_notifications: bool
    reminders_enabled: bool
    theme: str
    currency: str
    distance_unit: str = "miles"  # Default to miles

    class Config:
        from_attributes = True


class UserSettingsResponse(BaseModel):
    id: str
    email: str
    full_name: str
    preferences: PreferencesResponse

    class Config:
        from_attributes = True


class FeaturesResponse(BaseModel):
    enable_gemini_3_pro_preview: bool

    class Config:
        from_attributes = True
