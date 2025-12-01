from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_database
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactResponse, ContactListResponse, ContactStatusUpdate, ContactReply
from app.utils.auth import decode_token
from typing import Optional

router = APIRouter(prefix="/api/contact", tags=["contact"])


def get_current_user(authorization: Optional[str] = None):
    """Extract and verify user from token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


@router.post("", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db=Depends(get_database),
    authorization: Optional[str] = None
):
    """Create a new contact/support request"""
    
    # Get user ID from token if available
    user_id = None
    if authorization:
        try:
            user_id = get_current_user(authorization)
        except HTTPException:
            # Allow anonymous contact requests too
            pass
    
    contact_model = Contact(db)
    created_contact = contact_model.create(
        name=contact_data.name,
        email=contact_data.email,
        phone=contact_data.phone,
        subject=contact_data.subject,
        message=contact_data.message,
        agree_to_terms_and_privacy=contact_data.agreeToTermsAndPrivacy,
        agree_to_pdpa=contact_data.agreeToPDPA,
        user_id=user_id
    )
    
    return {
        "_id": created_contact["_id"],
        "name": created_contact["name"],
        "email": created_contact["email"],
        "phone": created_contact["phone"],
        "subject": created_contact["subject"],
        "message": created_contact["message"],
        "agreeToTermsAndPrivacy": created_contact["agreeToTermsAndPrivacy"],
        "agreeToPDPA": created_contact["agreeToPDPA"],
        "status": created_contact["status"],
        "user_id": created_contact.get("user_id"),
        "created_at": created_contact["created_at"],
        "updated_at": created_contact["updated_at"],
    }


@router.get("", response_model=ContactListResponse)
async def get_contacts(
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_database),
    authorization: Optional[str] = None
):
    """Get all contact requests for the current user"""
    
    user_id = get_current_user(authorization)
    
    contact_model = Contact(db)
    contacts = contact_model.get_by_user(user_id, skip=skip, limit=limit)
    
    # Convert ObjectId to string
    formatted_contacts = []
    for contact in contacts:
        formatted_contacts.append({
            "_id": str(contact["_id"]),
            "name": contact["name"],
            "email": contact["email"],
            "phone": contact.get("phone"),
            "subject": contact["subject"],
            "message": contact["message"],
            "agreeToTermsAndPrivacy": contact.get("agreeToTermsAndPrivacy", False),
            "agreeToPDPA": contact.get("agreeToPDPA", False),
            "status": contact.get("status", "open"),
            "user_id": str(contact.get("user_id")) if contact.get("user_id") else None,
            "created_at": contact["created_at"],
            "updated_at": contact["updated_at"],
            "replies": contact.get("replies", []),
        })
    
    return {
        "total": len(formatted_contacts),
        "contacts": formatted_contacts
    }


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    db=Depends(get_database),
    authorization: Optional[str] = None
):
    """Get a specific contact request"""
    
    user_id = get_current_user(authorization)
    
    contact_model = Contact(db)
    contact = contact_model.get_by_id(contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact request not found"
        )
    
    # Check if user owns this contact
    if contact.get("user_id") and str(contact["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this contact"
        )
    
    return {
        "_id": str(contact["_id"]),
        "name": contact["name"],
        "email": contact["email"],
        "phone": contact.get("phone"),
        "subject": contact["subject"],
        "message": contact["message"],
        "agreeToTermsAndPrivacy": contact.get("agreeToTermsAndPrivacy", False),
        "agreeToPDPA": contact.get("agreeToPDPA", False),
        "status": contact.get("status", "open"),
        "user_id": str(contact.get("user_id")) if contact.get("user_id") else None,
        "created_at": contact["created_at"],
        "updated_at": contact["updated_at"],
        "replies": contact.get("replies", []),
    }


@router.put("/{contact_id}/status", response_model=ContactResponse)
async def update_contact_status(
    contact_id: str,
    status_data: ContactStatusUpdate,
    db=Depends(get_database),
    authorization: Optional[str] = None
):
    """Update contact request status (admin only - for now we'll allow user to update)"""
    
    user_id = get_current_user(authorization)
    
    contact_model = Contact(db)
    contact = contact_model.get_by_id(contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact request not found"
        )
    
    # Check if user owns this contact
    if contact.get("user_id") and str(contact["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this contact"
        )
    
    contact_model.update_status(contact_id, status_data.status)
    updated_contact = contact_model.get_by_id(contact_id)
    
    return {
        "_id": str(updated_contact["_id"]),
        "name": updated_contact["name"],
        "email": updated_contact["email"],
        "phone": updated_contact.get("phone"),
        "subject": updated_contact["subject"],
        "message": updated_contact["message"],
        "agreeToTerms": updated_contact.get("agreeToTerms", False),
        "agreeToPrivacy": updated_contact.get("agreeToPrivacy", False),
        "agreeToConsent": updated_contact.get("agreeToConsent", False),
        "status": updated_contact.get("status", "open"),
        "user_id": str(updated_contact.get("user_id")) if updated_contact.get("user_id") else None,
        "created_at": updated_contact["created_at"],
        "updated_at": updated_contact["updated_at"],
        "replies": updated_contact.get("replies", []),
    }
