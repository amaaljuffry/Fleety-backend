from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from app.database import get_database
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse, ChangePasswordRequest, SubscriptionInfo
from app.utils.auth import hash_password, verify_password, create_access_token, decode_token
from app.services.email_service import send_password_reset_email
from app.middleware.subscription import get_subscription_status
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Pydantic models for password reset
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


@router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate, db=Depends(get_database)):
    user_model = User(db)
    
    # Check if user already exists
    existing_user = user_model.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    created_user = user_model.create(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    # Create access token
    access_token = create_access_token(data={"sub": created_user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=created_user["id"],
            email=created_user["email"],
            full_name=created_user["full_name"],
            is_active=created_user["is_active"]
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db=Depends(get_database)):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Login attempt for email: {user_data.email}")
    logger.info(f"Password received: {user_data.password} (len: {len(user_data.password)})")
    
    user_model = User(db)
    
    # Find user by email
    user = user_model.get_by_email(user_data.email)
    logger.info(f"User found: {user is not None}")
    
    if not user:
        logger.error(f"User not found: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    logger.info(f"User email: {user.get('email')}")
    hash_from_db = user.get('hashed_password')
    logger.info(f"Hash from user object: {hash_from_db}")
    logger.info(f"Hash type: {type(hash_from_db)}")
    logger.info(f"Hash is None: {hash_from_db is None}")
    
    if hash_from_db:
        logger.info(f"Hash length: {len(hash_from_db)}")
        logger.info(f"Hash starts with: {hash_from_db[:20]}")
    
    # Verify password
    try:
        password_valid = verify_password(user_data.password, user["hashed_password"])
        logger.info(f"Password verification result: {password_valid}")
    except Exception as e:
        logger.error(f"Password verification exception: {e}", exc_info=True)
        password_valid = False
    
    if not password_valid:
        logger.error(f"Password verification failed for user: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["id"]})
    logger.info(f"Login successful for user: {user_data.email}")
    
    # Get subscription status (synchronous call)
    subscription = get_subscription_status(user["id"])
    subscription_info = None
    if subscription:
        subscription_info = SubscriptionInfo(
            plan_id=subscription.get("plan_id"),
            status=subscription.get("status"),
            vehicle_count=subscription.get("vehicle_count"),
            current_period_end=subscription.get("current_period_end"),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            is_active=True
        )
    else:
        # Provide default free/trial subscription for development
        subscription_info = SubscriptionInfo(
            plan_id="free",
            status="active",
            vehicle_count=None,
            current_period_end=None,
            cancel_at_period_end=False,
            is_active=True
        )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            is_active=user["is_active"],
            subscription=subscription_info
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: str = Header(None), db=Depends(get_database)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization.replace("Bearer ", "")
    from app.utils.auth import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    user_model = User(db)
    user = user_model.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get subscription status (synchronous call)
    subscription = get_subscription_status(user["id"])
    subscription_info = None
    if subscription:
        subscription_info = SubscriptionInfo(
            plan_id=subscription.get("plan_id"),
            status=subscription.get("status"),
            vehicle_count=subscription.get("vehicle_count"),
            current_period_end=subscription.get("current_period_end"),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            is_active=True
        )
    else:
        # Provide default free/trial subscription for development
        subscription_info = SubscriptionInfo(
            plan_id="free",
            status="active",
            vehicle_count=None,
            current_period_end=None,
            cancel_at_period_end=False,
            is_active=True
        )
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        is_active=user["is_active"],
        subscription=subscription_info
    )


@router.put("/change-password")
async def change_password(password_data: ChangePasswordRequest, authorization: str = Header(None), db=Depends(get_database)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    user_model = User(db)
    user = user_model.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash new password and update
    new_hashed_password = hash_password(password_data.new_password)
    print(f"\nCHANGE PASSWORD DEBUG:")
    print(f"  User ID: {user_id}")
    print(f"  Old hash length: {len(user['hashed_password'])}")
    print(f"  New hash length: {len(new_hashed_password)}")
    print(f"  Calling update...")
    
    success = user_model.update(user_id, {"hashed_password": new_hashed_password})
    print(f"  Update success: {success}")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    # Verify update
    updated_user = user_model.get_by_id(user_id)
    print(f"  Updated hash matches new hash: {updated_user.get('hashed_password') == new_hashed_password}")
    print(f"  Updated hash length: {len(updated_user.get('hashed_password', ''))}\n")
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", response_model=ResetPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db=Depends(get_database)):
    """
    Request password reset. Sends email with reset link.
    """
    user_model = User(db)
    
    # Find user by email
    user = user_model.get_by_email(request.email)
    if not user:
        # Don't reveal if user exists (security best practice)
        return {"message": "If an account exists with that email, a password reset link will be sent"}
    
    # Generate reset token (valid for 1 hour)
    reset_token = secrets.token_urlsafe(32)
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Store reset token in database
    user_model.update(user["id"], {
        "reset_token": reset_token,
        "reset_token_expires": reset_token_expires
    })
    
    # Send reset email
    try:
        send_password_reset_email(
            user_email=user["email"],
            user_name=user.get("full_name", "User"),
            reset_token=reset_token
        )
    except Exception as e:
        print(f"Failed to send reset email: {str(e)}")
        # Don't fail the request, just log it
    
    return ResetPasswordResponse(message="If an account exists with that email, a password reset link will be sent")


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest, db=Depends(get_database)):
    """
    Reset password using reset token from email.
    """
    if not request.new_password or len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    user_model = User(db)
    
    # Find user by reset token
    user = user_model.get_by_reset_token(request.token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token has expired
    if user.get("reset_token_expires"):
        expires = user["reset_token_expires"]
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires)
        if expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one."
            )
    
    # Update password and clear reset token
    hashed_password = hash_password(request.new_password)
    user_model.update(user["id"], {
        "hashed_password": hashed_password,
        "reset_token": None,
        "reset_token_expires": None
    })
    
    return ResetPasswordResponse(message="Password reset successfully. You can now login with your new password.")
