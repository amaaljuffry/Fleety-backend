from fastapi import APIRouter, HTTPException, Header, status, Depends
from app.database import get_database
from app.models.user import User
from app.schemas.settings import PreferencesUpdate, PreferencesResponse, UserSettingsResponse, FeaturesResponse
from app.utils.auth import decode_token
from bson import ObjectId
import logging
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_current_user_id(authorization: str = Header(None)):
    """Extract and verify user_id from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return payload.get("sub")


@router.get("/features", response_model=FeaturesResponse)
async def get_features():
    """Get global feature flags for all clients."""
    try:
        return FeaturesResponse(
            enable_gemini_3_pro_preview=bool(settings.enable_gemini_3_pro_preview)
        )
    except Exception as e:
        logger.error(f"Error getting features: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/preferences", response_model=UserSettingsResponse)
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    """Get user preferences"""
    try:
        db = get_database()
        user_model = User(db)
        user = user_model.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Merge stored preferences with defaults
        stored_prefs = user.get("preferences", {})
        preferences = {
            "email_notifications": stored_prefs.get("email_notifications", True),
            "reminders_enabled": stored_prefs.get("reminders_enabled", True),
            "theme": stored_prefs.get("theme", "light"),
            "currency": stored_prefs.get("currency", "USD"),
            "distance_unit": stored_prefs.get("distance_unit", "miles")
        }
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "preferences": preferences
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/preferences", response_model=UserSettingsResponse)
async def update_preferences(
    data: PreferencesUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update user preferences"""
    try:
        db = get_database()
        user_model = User(db)
        user = user_model.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update only provided fields
        update_dict = {}
        if data.email_notifications is not None:
            update_dict["preferences.email_notifications"] = data.email_notifications
        if data.reminders_enabled is not None:
            update_dict["preferences.reminders_enabled"] = data.reminders_enabled
        if data.theme is not None:
            update_dict["preferences.theme"] = data.theme
        if data.currency is not None:
            update_dict["preferences.currency"] = data.currency
        if data.distance_unit is not None:
            update_dict["preferences.distance_unit"] = data.distance_unit
        
        if update_dict:
            success = user_model.update(user_id, update_dict)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update preferences")
        
        # Get updated user
        updated_user = user_model.get_by_id(user_id)
        # Merge stored preferences with defaults
        stored_prefs = updated_user.get("preferences", {})
        preferences = {
            "email_notifications": stored_prefs.get("email_notifications", True),
            "reminders_enabled": stored_prefs.get("reminders_enabled", True),
            "theme": stored_prefs.get("theme", "light"),
            "currency": stored_prefs.get("currency", "USD"),
            "distance_unit": stored_prefs.get("distance_unit", "miles")
        }
        
        return {
            "id": str(updated_user["_id"]),
            "email": updated_user["email"],
            "full_name": updated_user["full_name"],
            "preferences": preferences
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/account")
async def get_account_info(user_id: str = Depends(get_current_user_id)):
    """Get user account information"""
    try:
        db = get_database()
        user_model = User(db)
        user = user_model.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "is_active": user.get("is_active", True),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/account")
async def delete_account(user_id: str = Depends(get_current_user_id)):
    """Delete user account"""
    try:
        db = get_database()
        
        # Get all vehicles for this user to delete their maintenance and reminders
        vehicles = list(db["vehicles"].find({"user_id": user_id}))
        vehicle_ids = [str(v["_id"]) for v in vehicles]
        
        # Delete maintenance and reminders for each vehicle
        for vehicle_id in vehicle_ids:
            db["maintenance"].delete_many({"vehicle_id": vehicle_id})
            db["reminders"].delete_many({"vehicle_id": vehicle_id})
        
        # Delete vehicles
        db["vehicles"].delete_many({"user_id": user_id})
        
        # Delete user
        result = db["users"].delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Account deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
