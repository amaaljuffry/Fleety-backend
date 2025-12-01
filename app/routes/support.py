from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from app.database import get_database
from app.models.contact import Contact
from app.services.rag_service import RAGService
from app.services.email_service import send_support_email
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/support", tags=["support"])


class SupportInquiry(BaseModel):
    name: str
    email: EmailStr
    inquiry: str


class SupportResponse(BaseModel):
    success: bool
    message: str
    answered_by_ai: bool
    answer: Optional[str] = None
    ticket_id: Optional[str] = None


def get_current_user_id(authorization: str = Header(None)) -> Optional[str]:
    """Extract user ID from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        from app.utils.auth import decode_token
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


@router.post("/inquire", response_model=SupportResponse)
async def submit_support_inquiry(
    inquiry: SupportInquiry,
    db=Depends(get_database),
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Submit a support inquiry.
    - AI attempts to answer using FAQ system
    - If AI confidence is low, creates a support ticket and emails admin
    - Returns the AI answer or confirmation of ticket creation
    """
    
    try:
        # Try to get AI answer first
        rag_service = RAGService()
        ai_response = await rag_service.search_and_generate(inquiry.inquiry)
        
        # Check if we got a meaningful answer
        # If answer is too generic or confidence is low, create ticket and email
        is_ai_answer = (
            ai_response and 
            ai_response.get("answer") and 
            len(ai_response.get("answer", "")) > 20 and
            "don't have" not in ai_response.get("answer", "").lower() and
            "not found" not in ai_response.get("answer", "").lower()
        )
        
        if is_ai_answer:
            # AI provided a good answer, return it
            return SupportResponse(
                success=True,
                message="Your inquiry has been answered",
                answered_by_ai=True,
                answer=ai_response.get("answer")
            )
        else:
            # AI couldn't answer well, create support ticket
            contact_model = Contact(db)
            contact = contact_model.create(
                name=inquiry.name,
                email=inquiry.email,
                phone="",  # Optional for chat support
                subject="Chat Support - " + inquiry.inquiry[:50],
                message=inquiry.inquiry,
                agree_to_terms_and_privacy=True,
                agree_to_pdpa=True,
                user_id=user_id
            )
            
            # Send email to admin
            ticket_id = contact.get("_id", "")
            try:
                send_support_email(
                    customer_name=inquiry.name,
                    customer_email=inquiry.email,
                    inquiry=inquiry.inquiry,
                    ticket_id=ticket_id
                )
            except Exception as e:
                print(f"Warning: Email not sent for ticket {ticket_id}: {str(e)}")
            
            return SupportResponse(
                success=True,
                message="Your inquiry has been received. Our support team will respond soon.",
                answered_by_ai=False,
                ticket_id=ticket_id
            )
    
    except Exception as e:
        print(f"Support inquiry error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process inquiry"
        )
