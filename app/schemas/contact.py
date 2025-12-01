from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class ContactCreate(BaseModel):
    """Schema for creating a contact request"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    agreeToTermsAndPrivacy: bool = Field(..., description="Must agree to Terms and Privacy Policy")
    agreeToPDPA: bool = Field(..., description="Must consent to PDPA data processing")


class ContactResponse(BaseModel):
    """Schema for contact response"""
    id: str = Field(alias="_id")
    name: str
    email: str
    phone: Optional[str] = None
    subject: str
    message: str
    agreeToTermsAndPrivacy: bool
    agreeToPDPA: bool
    status: str  # open, in_progress, closed
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    replies: Optional[List[dict]] = None
    
    class Config:
        populate_by_name = True


class ContactListResponse(BaseModel):
    """Schema for contact list response"""
    total: int
    contacts: List[ContactResponse]


class ContactStatusUpdate(BaseModel):
    """Schema for updating contact status"""
    status: str = Field(..., pattern="^(open|in_progress|closed)$")


class ContactReply(BaseModel):
    """Schema for adding a reply to a contact request"""
    message: str = Field(..., min_length=5, max_length=5000)
