from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class PublicContactCreate(BaseModel):
    """Schema for creating a public contact inquiry from landing page"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    agreeToTermsAndPrivacy: bool = Field(..., description="Must agree to Terms and Privacy Policy")
    agreeToPDPA: bool = Field(..., description="Must consent to PDPA data processing")


class PublicContactResponse(BaseModel):
    """Schema for public contact response"""
    status: str
    message: str
    inquiry_id: str


class PublicContactInquiry(BaseModel):
    """Internal schema for database response"""
    id: str = Field(alias="_id")
    name: str
    email: str
    phone: Optional[str] = None
    subject: str
    message: str
    agreeToTermsAndPrivacy: bool
    agreeToPDPA: bool
    status: str  # new, read, contacted, closed
    created_at: datetime
    updated_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        populate_by_name = True
