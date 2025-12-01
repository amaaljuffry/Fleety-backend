from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.database import get_database
from app.models.newsletter import Newsletter

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


class NewsletterSubscribe(BaseModel):
    email: EmailStr


class NewsletterResponse(BaseModel):
    _id: str
    email: str
    subscribed: bool
    created_at: str


@router.post("/subscribe")
async def subscribe_newsletter(
    data: NewsletterSubscribe,
    db=Depends(get_database)
):
    """Subscribe to the newsletter"""
    try:
        newsletter = Newsletter(db)
        result = newsletter.subscribe(data.email)
        return {
            "success": True,
            "message": "Successfully subscribed to newsletter",
            "data": {
                "_id": result.get("_id"),
                "email": result.get("email"),
                "subscribed": result.get("subscribed")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/unsubscribe")
async def unsubscribe_newsletter(
    data: NewsletterSubscribe,
    db=Depends(get_database)
):
    """Unsubscribe from the newsletter"""
    try:
        newsletter = Newsletter(db)
        result = newsletter.unsubscribe(data.email)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        return {
            "success": True,
            "message": "Successfully unsubscribed from newsletter",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/status/{email}")
async def get_subscription_status(
    email: str,
    db=Depends(get_database)
):
    """Get subscription status for an email"""
    try:
        newsletter = Newsletter(db)
        subscription = newsletter.get_by_email(email)
        if not subscription:
            return {
                "success": True,
                "subscribed": False,
                "message": "Email not subscribed"
            }
        return {
            "success": True,
            "subscribed": subscription["subscribed"],
            "email": subscription["email"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
