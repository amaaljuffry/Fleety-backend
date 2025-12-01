from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
from app.models.waitlist import Waitlist
from app.services.email_service import resend_service
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


class WaitlistJoinRequest(BaseModel):
    """Request body for joining waitlist"""
    name: str
    email: EmailStr

    @validator("name")
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Name must be less than 100 characters")
        return v.strip()

    @validator("email")
    def email_valid(cls, v):
        # Additional validation beyond EmailStr
        if len(v) > 255:
            raise ValueError("Email too long")
        return v.lower().strip()


class WaitlistResponse(BaseModel):
    """Response from waitlist endpoint"""
    success: bool
    message: str
    email: str = None
    id: str = None


class WaitlistStatsResponse(BaseModel):
    """Waitlist statistics response"""
    total_signups: int
    confirmed: int
    converted: int
    pending: int
    conversion_rate: float
    by_source: dict


@router.post("/join", response_model=WaitlistResponse)
async def join_waitlist(request: WaitlistJoinRequest):
    """
    Add a new subscriber to the waitlist
    
    Request body:
    {
        "name": "John Doe",
        "email": "john@example.com"
    }
    
    Response:
    {
        "success": true,
        "message": "Successfully added to waitlist!",
        "email": "john@example.com",
        "id": "507f1f77bcf86cd799439011"
    }
    """
    try:
        logger.info(f"Waitlist join request: {request.email}")

        # Add to waitlist
        result = await Waitlist.add_to_waitlist(
            name=request.name,
            email=request.email,
            source="landing_page"
        )

        # Send confirmation email (non-blocking, doesn't affect response)
        if result["success"]:
            try:
                await resend_service.send_waitlist_confirmation(
                    email=request.email,
                    name=request.name
                )
                logger.info(f"Confirmation email sent to {request.email}")
            except Exception as e:
                # Log but don't fail the request - user still added to waitlist
                logger.warning(f"Failed to send confirmation email to {request.email}: {str(e)}")

        return WaitlistResponse(
            success=result["success"],
            message=result["message"],
            email=result["email"],
            id=result["id"]
        )

    except ValueError as e:
        # Duplicate email or validation error
        logger.warning(f"Waitlist validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Error joining waitlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add to waitlist. Please try again."
        )


@router.get("/stats", response_model=WaitlistStatsResponse)
async def get_waitlist_stats():
    """
    Get waitlist statistics
    
    Returns:
    {
        "total_signups": 150,
        "confirmed": 120,
        "converted": 5,
        "pending": 25,
        "conversion_rate": 3.33,
        "by_source": {
            "landing_page": 120,
            "social": 20,
            "direct": 10
        }
    }
    """
    try:
        stats = await Waitlist.get_waitlist_stats()
        return WaitlistStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting waitlist stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get waitlist stats"
        )


@router.post("/confirm/{email}")
async def confirm_waitlist_email(email: str):
    """
    Confirm email address (for email verification flow)
    
    Response:
    {
        "success": true,
        "message": "Email confirmed"
    }
    """
    try:
        # Validate email format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        success = await Waitlist.mark_as_confirmed(email)

        if success:
            logger.info(f"Email confirmed: {email}")
            return {
                "success": True,
                "message": "Email confirmed"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found on waitlist"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm email"
        )


@router.post("/convert/{email}")
async def convert_waitlist_user(email: str, user_id: str):
    """
    Mark user as converted (became paying customer)
    
    Query params:
    - user_id: ID of created user account
    
    Response:
    {
        "success": true,
        "message": "User converted successfully"
    }
    """
    try:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        success = await Waitlist.mark_as_converted(email, user_id)

        if success:
            logger.info(f"Converted waitlist user: {email}")
            return {
                "success": True,
                "message": "User converted successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found on waitlist"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert user"
        )


@router.get("/list")
async def list_waitlist(
    limit: int = 100,
    skip: int = 0,
    status: str = None
):
    """
    Get all waitlist entries (admin only)
    
    Query params:
    - limit: Max records (default: 100)
    - skip: Pagination offset (default: 0)
    - status: Filter by status (pending, confirmed, converted)
    
    Response:
    [
        {
            "id": "507f1f77bcf86cd799439011",
            "name": "John Doe",
            "email": "john@example.com",
            "status": "pending",
            "joined_at": "2024-01-15T10:30:00",
            "is_converted": false
        },
        ...
    ]
    """
    try:
        entries = await Waitlist.get_all_waitlist(
            limit=limit,
            skip=skip,
            status_filter=status
        )
        return {
            "success": True,
            "total": len(entries),
            "data": entries
        }

    except Exception as e:
        logger.error(f"Error listing waitlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list waitlist"
        )


@router.get("/export")
async def export_waitlist():
    """
    Export all waitlist entries (CSV format via download)
    
    Response:
    [
        {
            "name": "John Doe",
            "email": "john@example.com",
            "joined_at": "2024-01-15T10:30:00",
            "status": "pending",
            "is_converted": false
        },
        ...
    ]
    """
    try:
        entries = await Waitlist.export_waitlist()
        return {
            "success": True,
            "total": len(entries),
            "data": entries
        }

    except Exception as e:
        logger.error(f"Error exporting waitlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export waitlist"
        )


@router.get("/unsubscribe")
async def unsubscribe_from_waitlist(email: str):
    """
    Unsubscribe an email from the waitlist
    
    Query parameters:
    - email: The email address to unsubscribe
    
    Response:
    {
        "success": true,
        "message": "Successfully unsubscribed from emails"
    }
    """
    try:
        if not email:
            raise ValueError("Email parameter is required")
        
        logger.info(f"Unsubscribe request: {email}")
        
        # Update waitlist entry to mark as unsubscribed
        result = await Waitlist.unsubscribe(email)
        
        if result:
            logger.info(f"Successfully unsubscribed: {email}")
            return {
                "success": True,
                "message": f"You have been unsubscribed from Fleety emails. We'll miss you!"
            }
        else:
            logger.warning(f"Email not found in waitlist: {email}")
            return {
                "success": True,
                "message": "Email not found, but you won't receive any more emails from us."
            }
    
    except Exception as e:
        logger.error(f"Error processing unsubscribe: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process unsubscribe request"
        )