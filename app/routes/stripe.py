"""
Stripe Routes for Fleety Payment Integration
Handles Stripe Checkout Sessions and Webhooks
"""
import os
import stripe
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr

from app.models.subscription import (
    Subscription, 
    SubscriptionCreate, 
    EnterpriseLead, 
    EnterpriseLeadCreate
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stripe", tags=["Stripe"])

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

# Stripe Price IDs - Set these in your .env file
# These are created in your Stripe Dashboard
STRIPE_PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter_id"),
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_id"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_id"),
}

# Plan prices in MYR (cents)
PLAN_PRICES = {
    "starter": 1990,      # MYR 19.90 per vehicle/month
    "pro": 3490,          # MYR 34.90 per vehicle/month
    "enterprise": 4990,   # MYR 49.90 per vehicle/month
}


# Request/Response Models
class CheckoutRequest(BaseModel):
    """Request body for creating checkout session"""
    plan_id: str = Field(..., pattern="^(starter|pro|enterprise)$")
    vehicle_count: int = Field(..., ge=1, le=500)
    user_email: Optional[str] = None
    user_id: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response for checkout session"""
    url: str
    session_id: str


class EnterpriseContactRequest(BaseModel):
    """Request body for enterprise contact form"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    company_name: str = Field(..., min_length=2, max_length=200)
    company_size: str = Field(..., pattern="^(1-10|11-50|51-200|201-500|500\\+)$")
    fleet_size: int = Field(..., ge=1, le=10000)
    message: Optional[str] = Field(None, max_length=1000)


class SubscriptionStatusResponse(BaseModel):
    """Response for subscription status"""
    has_subscription: bool
    plan_id: Optional[str] = None
    vehicle_count: Optional[int] = None
    status: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    stripe_customer_id: Optional[str] = None


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: CheckoutRequest):
    """
    Create a Stripe Checkout Session for subscription.
    
    - **plan_id**: 'starter', 'pro', or 'enterprise'
    - **vehicle_count**: Number of vehicles (1-500)
    - **user_email**: Optional email for prefilling
    - **user_id**: Optional user ID for tracking
    """
    try:
        if request.plan_id not in STRIPE_PRICE_IDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan_id: {request.plan_id}"
            )

        price_id = STRIPE_PRICE_IDS[request.plan_id]
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": request.vehicle_count,
                }
            ],
            success_url=f"{FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/checkout/cancelled",
            customer_email=request.user_email,
            metadata={
                "plan_id": request.plan_id,
                "vehicle_count": str(request.vehicle_count),
                "user_id": request.user_id or "anonymous",
            },
            subscription_data={
                "metadata": {
                    "plan_id": request.plan_id,
                    "vehicle_count": str(request.vehicle_count),
                    "user_id": request.user_id or "anonymous",
                }
            },
            allow_promotion_codes=True,
            billing_address_collection="required",
        )

        logger.info(f"Created checkout session: {checkout_session.id} for plan: {request.plan_id}")
        
        return CheckoutResponse(
            url=checkout_session.url,
            session_id=checkout_session.id
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for subscription events.
    
    Events handled:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Received webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(data)
        
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(data)
        
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(data)
        
        elif event_type == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(data)
        
        elif event_type == "invoice.payment_failed":
            await handle_invoice_payment_failed(data)
        
        else:
            logger.info(f"Unhandled event type: {event_type}")

    except Exception as e:
        logger.error(f"Error handling webhook {event_type}: {str(e)}")
        # Don't raise - return 200 to acknowledge receipt
        
    return {"status": "received"}


async def handle_checkout_completed(session: dict):
    """Handle successful checkout completion"""
    logger.info(f"Processing checkout.session.completed: {session['id']}")
    
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    metadata = session.get("metadata", {})
    
    if not subscription_id:
        logger.warning("No subscription ID in checkout session")
        return

    # Retrieve full subscription details from Stripe
    subscription = stripe.Subscription.retrieve(subscription_id)
    
    # Create subscription record in MongoDB
    subscription_data = SubscriptionCreate(
        user_id=metadata.get("user_id", "unknown"),
        plan_id=metadata.get("plan_id", "starter"),
        vehicle_count=int(metadata.get("vehicle_count", 1)),
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        stripe_price_id=subscription["items"]["data"][0]["price"]["id"],
        status=subscription["status"],
    )
    
    Subscription.create(subscription_data)
    logger.info(f"Created subscription record for: {subscription_id}")


async def handle_subscription_updated(subscription: dict):
    """Handle subscription updates"""
    logger.info(f"Processing subscription.updated: {subscription['id']}")
    
    update_data = {
        "status": subscription["status"],
        "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]),
        "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]),
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
    }
    
    # Update vehicle count if changed
    metadata = subscription.get("metadata", {})
    if "vehicle_count" in metadata:
        update_data["vehicle_count"] = int(metadata["vehicle_count"])
    
    if "plan_id" in metadata:
        update_data["plan_id"] = metadata["plan_id"]
    
    Subscription.update_by_stripe_subscription_id(
        subscription["id"],
        update_data
    )
    logger.info(f"Updated subscription: {subscription['id']}")


async def handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation/deletion"""
    logger.info(f"Processing subscription.deleted: {subscription['id']}")
    
    Subscription.update_by_stripe_subscription_id(
        subscription["id"],
        {"status": "cancelled"}
    )
    logger.info(f"Cancelled subscription: {subscription['id']}")


async def handle_invoice_payment_succeeded(invoice: dict):
    """Handle successful invoice payment"""
    subscription_id = invoice.get("subscription")
    if subscription_id:
        logger.info(f"Payment succeeded for subscription: {subscription_id}")
        Subscription.update_by_stripe_subscription_id(
            subscription_id,
            {"status": "active"}
        )


async def handle_invoice_payment_failed(invoice: dict):
    """Handle failed invoice payment"""
    subscription_id = invoice.get("subscription")
    if subscription_id:
        logger.warning(f"Payment failed for subscription: {subscription_id}")
        Subscription.update_by_stripe_subscription_id(
            subscription_id,
            {"status": "past_due"}
        )


@router.post("/enterprise-contact")
async def submit_enterprise_contact(request: EnterpriseContactRequest):
    """
    Submit enterprise contact form.
    
    Stores lead in MongoDB for sales team follow-up.
    """
    try:
        lead_data = EnterpriseLeadCreate(
            name=request.name,
            email=request.email,
            company_name=request.company_name,
            company_size=request.company_size,
            fleet_size=request.fleet_size,
            message=request.message,
        )
        
        EnterpriseLead.create(lead_data)
        
        logger.info(f"Enterprise lead created: {request.email}")
        
        # TODO: Send notification email to sales team
        # await send_sales_notification(lead_data)
        
        return {
            "success": True,
            "message": "Thank you for your interest! Our sales team will contact you within 24 hours."
        }
        
    except Exception as e:
        logger.error(f"Enterprise contact error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit contact form"
        )


@router.get("/subscription-status/{user_id}", response_model=SubscriptionStatusResponse)
async def get_subscription_status(user_id: str):
    """
    Get subscription status for a user.
    """
    try:
        subscription = Subscription.find_by_user_id(user_id)
        
        if not subscription:
            return SubscriptionStatusResponse(has_subscription=False)
        
        return SubscriptionStatusResponse(
            has_subscription=True,
            plan_id=subscription.get("plan_id"),
            vehicle_count=subscription.get("vehicle_count"),
            status=subscription.get("status"),
            current_period_end=subscription.get("current_period_end"),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            stripe_customer_id=subscription.get("stripe_customer_id"),
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription status"
        )


@router.post("/create-billing-portal/{user_id}")
async def create_billing_portal(user_id: str):
    """
    Create a Stripe Billing Portal session for the user.
    Allows users to manage payment methods, view invoices, and update subscription.
    """
    try:
        subscription = Subscription.find_by_user_id(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found for this user"
            )
        
        stripe_customer_id = subscription.get("stripe_customer_id")
        if not stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer ID found"
            )
        
        # Create billing portal session
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{FRONTEND_URL}/billing",
        )
        
        return {
            "success": True,
            "url": session.url
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe billing portal error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create billing portal session"
        )


@router.post("/cancel-subscription/{user_id}")
async def cancel_subscription(user_id: str):
    """
    Cancel a user's subscription at period end.
    """
    try:
        subscription = Subscription.find_by_user_id(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Cancel in Stripe (at period end)
        stripe.Subscription.modify(
            subscription["stripe_subscription_id"],
            cancel_at_period_end=True
        )
        
        # Update in MongoDB
        Subscription.update_by_stripe_subscription_id(
            subscription["stripe_subscription_id"],
            {"cancel_at_period_end": True}
        )
        
        return {
            "success": True,
            "message": "Subscription will be cancelled at the end of the current billing period."
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe cancellation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.post("/update-vehicle-count/{user_id}")
async def update_vehicle_count(user_id: str, vehicle_count: int = Query(..., ge=1, le=500)):
    """
    Update the vehicle count for a subscription.
    This updates the quantity in Stripe and triggers prorated billing.
    """
    try:
        subscription = Subscription.find_by_user_id(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Get Stripe subscription
        stripe_sub = stripe.Subscription.retrieve(subscription["stripe_subscription_id"])
        
        # Update quantity in Stripe
        stripe.Subscription.modify(
            subscription["stripe_subscription_id"],
            items=[{
                "id": stripe_sub["items"]["data"][0]["id"],
                "quantity": vehicle_count,
            }],
            proration_behavior="create_prorations",
            metadata={
                "vehicle_count": str(vehicle_count),
            }
        )
        
        # Update in MongoDB
        Subscription.update_by_stripe_subscription_id(
            subscription["stripe_subscription_id"],
            {"vehicle_count": vehicle_count}
        )
        
        return {
            "success": True,
            "message": f"Vehicle count updated to {vehicle_count}. Prorated charges will apply."
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vehicle count"
        )


@router.get("/plans")
async def get_plans():
    """
    Get available pricing plans.
    """
    return {
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price_per_vehicle": 19.90,
                "currency": "MYR",
                "description": "Perfect for small local fleets.",
                "features": [
                    "Maintenance logging per vehicle",
                    "Date & mileage-based reminders",
                    "Cost tracking per vehicle",
                    "Basic email alerts",
                    "Up to 3 fleet managers",
                    "Monthly cost reports",
                    "CSV exports"
                ]
            },
            {
                "id": "pro",
                "name": "Professional",
                "price_per_vehicle": 34.90,
                "currency": "MYR",
                "description": "For growing fleets needing advanced features.",
                "popular": True,
                "features": [
                    "Everything in Starter +",
                    "Unlimited fleet managers",
                    "SMS alerts (via Twilio)",
                    "Receipt photo storage (10GB)",
                    "Driver assignment tracking",
                    "Fuel cost tracking",
                    "Advanced analytics & trends",
                    "Monthly maintenance forecasting",
                    "Preventive maintenance scheduling",
                    "API access (read-only)"
                ]
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price_per_vehicle": 49.90,
                "currency": "MYR",
                "description": "Full control for large organizations.",
                "features": [
                    "Everything in Professional +",
                    "Unlimited receipt storage (100GB)",
                    "Custom workshop integrations",
                    "Multi-location support",
                    "Full API access (read/write)",
                    "Webhook integrations",
                    "Custom reports & dashboards",
                    "Dedicated account manager",
                    "Priority phone support (24/5)",
                    "Service history exports for resale",
                    "Insurance claim integration"
                ]
            }
        ]
    }


@router.get("/debug/init-collections")
async def init_collections():
    """
    Initialize subscription collections in MongoDB.
    Creates the collections and indexes if they don't exist.
    """
    from app.database import get_database
    
    db = get_database()
    
    # Get existing collections
    existing = db.list_collection_names()
    created = []
    
    # Create subscriptions collection if not exists
    if "subscriptions" not in existing:
        db.create_collection("subscriptions")
        created.append("subscriptions")
    
    # Create indexes for subscriptions
    db.subscriptions.create_index("user_id")
    db.subscriptions.create_index("stripe_subscription_id", unique=True, sparse=True)
    db.subscriptions.create_index("stripe_customer_id")
    
    # Create enterprise_leads collection if not exists
    if "enterprise_leads" not in existing:
        db.create_collection("enterprise_leads")
        created.append("enterprise_leads")
    
    # Create index for enterprise_leads
    db.enterprise_leads.create_index("email")
    db.enterprise_leads.create_index("created_at")
    
    return {
        "success": True,
        "collections_created": created,
        "all_collections": db.list_collection_names(),
        "indexes": {
            "subscriptions": list(db.subscriptions.index_information().keys()),
            "enterprise_leads": list(db.enterprise_leads.index_information().keys())
        }
    }


class TestSubscriptionRequest(BaseModel):
    """Request for creating a test subscription"""
    user_id: str
    plan_id: str = "starter"
    vehicle_count: int = 1


@router.post("/debug/create-test-subscription")
async def create_test_subscription(request: TestSubscriptionRequest):
    """
    Create a test subscription for development/testing.
    WARNING: Only use in development!
    """
    from app.database import get_database
    from datetime import datetime, timedelta
    
    db = get_database()
    
    # Check if user already has a subscription
    existing = db.subscriptions.find_one({"user_id": request.user_id})
    if existing:
        return {
            "success": False,
            "message": "User already has a subscription",
            "subscription": {
                "user_id": existing["user_id"],
                "plan_id": existing["plan_id"],
                "status": existing["status"]
            }
        }
    
    # Create test subscription
    now = datetime.utcnow()
    subscription_doc = {
        "user_id": request.user_id,
        "plan_id": request.plan_id,
        "vehicle_count": request.vehicle_count,
        "stripe_customer_id": f"cus_test_{request.user_id[:8]}",
        "stripe_subscription_id": f"sub_test_{request.user_id[:8]}",
        "stripe_price_id": f"price_{request.plan_id}_test",
        "status": "active",
        "current_period_start": now,
        "current_period_end": now + timedelta(days=30),
        "cancel_at_period_end": False,
        "created_at": now,
        "updated_at": now
    }
    
    result = db.subscriptions.insert_one(subscription_doc)
    subscription_doc["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "message": "Test subscription created",
        "subscription": {
            "id": subscription_doc["_id"],
            "user_id": subscription_doc["user_id"],
            "plan_id": subscription_doc["plan_id"],
            "vehicle_count": subscription_doc["vehicle_count"],
            "status": subscription_doc["status"],
            "current_period_end": subscription_doc["current_period_end"].isoformat()
        }
    }
