from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SubscriptionInfo(BaseModel):
    """Subscription status info included in responses"""
    plan_id: Optional[str] = None
    status: Optional[str] = None
    vehicle_count: Optional[int] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    is_active: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    subscription: Optional[SubscriptionInfo] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

