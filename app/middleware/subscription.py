"""
Subscription Middleware for Fleety
Checks subscription status for protected routes
"""
from typing import Optional, List
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from datetime import datetime

from app.models.subscription import Subscription

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Plan hierarchy for access control
PLAN_HIERARCHY = {
    "starter": 1,
    "pro": 2,
    "enterprise": 3,
}


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def get_subscription_status(user_id: str) -> Optional[dict]:
    """
    Get subscription status for a user.
    Returns None if no active subscription.
    """
    subscription = Subscription.find_by_user_id(user_id)
    
    if not subscription:
        return None
    
    # Check if subscription is active
    if subscription.get("status") not in ["active", "trialing"]:
        return None
    
    # Check if subscription has expired
    current_period_end = subscription.get("current_period_end")
    if current_period_end:
        if isinstance(current_period_end, str):
            end_date = datetime.fromisoformat(current_period_end.replace("Z", "+00:00"))
        else:
            end_date = current_period_end
        
        if end_date < datetime.now(end_date.tzinfo):
            return None
    
    return {
        "plan_id": subscription.get("plan_id"),
        "status": subscription.get("status"),
        "vehicle_count": subscription.get("vehicle_count"),
        "current_period_end": str(current_period_end) if current_period_end else None,
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
    }


async def require_active_subscription(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency that requires an active subscription.
    Returns user info with subscription details.
    """
    user_id = await get_current_user_id(credentials)
    subscription = get_subscription_status(user_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "subscription_required",
                "message": "An active subscription is required to access this resource",
                "upgrade_url": "/pricing"
            }
        )
    
    return {
        "user_id": user_id,
        "subscription": subscription
    }


def require_plan(allowed_plans: List[str]):
    """
    Dependency factory that requires a specific plan level.
    
    Usage:
        @router.get("/analytics")
        async def get_analytics(user = Depends(require_plan(["pro", "enterprise"]))):
            ...
    """
    async def check_plan(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict:
        user_id = await get_current_user_id(credentials)
        subscription = get_subscription_status(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "subscription_required",
                    "message": "An active subscription is required",
                    "upgrade_url": "/pricing"
                }
            )
        
        user_plan = subscription.get("plan_id")
        
        if user_plan not in allowed_plans:
            # Check plan hierarchy
            user_level = PLAN_HIERARCHY.get(user_plan, 0)
            required_level = min(PLAN_HIERARCHY.get(p, 999) for p in allowed_plans)
            
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "message": f"This feature requires a {allowed_plans[0]} plan or higher",
                        "current_plan": user_plan,
                        "required_plans": allowed_plans,
                        "upgrade_url": "/pricing"
                    }
                )
        
        return {
            "user_id": user_id,
            "subscription": subscription
        }
    
    return check_plan


class SubscriptionGate:
    """
    Flexible subscription gate for route protection.
    
    Usage:
        gate = SubscriptionGate(require_subscription=True, min_plan="pro")
        
        @router.get("/analytics")
        async def get_analytics(user = Depends(gate)):
            ...
    """
    
    def __init__(
        self,
        require_subscription: bool = True,
        min_plan: Optional[str] = None,
        allowed_plans: Optional[List[str]] = None,
        allow_trial: bool = True,
    ):
        self.require_subscription = require_subscription
        self.min_plan = min_plan
        self.allowed_plans = allowed_plans
        self.allow_trial = allow_trial
    
    async def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict:
        user_id = await get_current_user_id(credentials)
        
        if not self.require_subscription:
            return {"user_id": user_id, "subscription": None}
        
        subscription = get_subscription_status(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "subscription_required",
                    "message": "An active subscription is required",
                    "upgrade_url": "/pricing"
                }
            )
        
        # Check trial status
        if subscription.get("status") == "trialing" and not self.allow_trial:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "paid_subscription_required",
                    "message": "This feature requires a paid subscription",
                    "upgrade_url": "/pricing"
                }
            )
        
        # Check plan level
        if self.min_plan:
            user_level = PLAN_HIERARCHY.get(subscription.get("plan_id"), 0)
            required_level = PLAN_HIERARCHY.get(self.min_plan, 0)
            
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "message": f"This feature requires a {self.min_plan} plan or higher",
                        "current_plan": subscription.get("plan_id"),
                        "required_plan": self.min_plan,
                        "upgrade_url": "/pricing"
                    }
                )
        
        # Check specific allowed plans
        if self.allowed_plans:
            if subscription.get("plan_id") not in self.allowed_plans:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_not_allowed",
                        "message": f"This feature requires one of: {', '.join(self.allowed_plans)}",
                        "current_plan": subscription.get("plan_id"),
                        "allowed_plans": self.allowed_plans,
                        "upgrade_url": "/pricing"
                    }
                )
        
        return {
            "user_id": user_id,
            "subscription": subscription
        }
