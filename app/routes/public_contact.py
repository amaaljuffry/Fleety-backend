from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.database import get_database
from app.models.public_contact import PublicContactInquiry
from app.schemas.public_contact import PublicContactCreate, PublicContactResponse
from app.services.email_service import ResendEmailService
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/contact", tags=["public-contact"])

# Initialize email service
email_service = ResendEmailService()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    if request.client:
        return request.client.host
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("user-agent", "unknown")


@router.post("", response_model=PublicContactResponse, status_code=201)
async def create_public_contact_inquiry(
    inquiry_data: PublicContactCreate,
    request: Request,
    db=Depends(get_database)
):
    """
    Create a new public contact inquiry from landing page
    
    This endpoint is public and does not require authentication.
    Includes rate limiting and anti-spam protection.
    """
    
    # Extract client information
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    logger.info(f"New contact inquiry from {inquiry_data.email} (IP: {client_ip})")
    
    # Rate limiting: Check if email has submitted too many inquiries in last 24 hours
    inquiry_model = PublicContactInquiry(db)
    inquiry_count = inquiry_model.count_by_email(inquiry_data.email, hours=24)
    
    if inquiry_count >= 3:
        logger.warning(f"Rate limit exceeded for email: {inquiry_data.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many inquiries from this email. Please try again later."
        )
    
    try:
        # Create the inquiry
        created_inquiry = inquiry_model.create(
            name=inquiry_data.name,
            email=inquiry_data.email,
            phone=inquiry_data.phone or "",
            subject=inquiry_data.subject,
            message=inquiry_data.message,
            agree_to_terms_and_privacy=inquiry_data.agreeToTermsAndPrivacy,
            agree_to_pdpa=inquiry_data.agreeToPDPA,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Send confirmation email to user
        await send_user_confirmation_email(inquiry_data.name, inquiry_data.email)
        
        # Send admin notification email
        await send_admin_notification_email(inquiry_data)
        
        logger.info(f"Contact inquiry created successfully: {created_inquiry['_id']}")
        
        return {
            "status": "ok",
            "message": "Thank you for your inquiry. We'll get back to you soon.",
            "inquiry_id": str(created_inquiry["_id"])
        }
        
    except Exception as e:
        logger.error(f"Error creating contact inquiry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your inquiry. Please try again later."
        )


async def send_user_confirmation_email(name: str, email: str) -> bool:
    """Send confirmation email to the user who submitted the form"""
    
    html_content = f"""
    <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="http://localhost:8000/public/FL_Logo.svg" alt="Fleety Logo" style="height: 50px; margin-bottom: 10px;">
                    <p style="color: #666; font-size: 12px; margin: 0; font-style: italic;">Smarter Fleet Management</p>
                </div>
                
                <h1 style="color: #000; margin: 0 0 20px 0; font-size: 28px;">We've Received Your Message</h1>
                
                <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    Hi {name},
                </p>
                
                <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    Thank you for reaching out to Fleety! We've received your inquiry and our team will review it shortly.
                </p>
                
                <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    We typically respond to all inquiries within 24 hours during business hours. If your message is urgent, please feel free to call our support team.
                </p>
                
                <div style="background-color: #f9f9f9; border-left: 4px solid #000; padding: 20px; margin: 30px 0;">
                    <h3 style="color: #000; margin: 0 0 10px 0;">Quick Links:</h3>
                    <ul style="color: #555; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
                        <li><a href="http://localhost:3000/about" style="color: #0066cc; text-decoration: none;">Learn about Fleety</a></li>
                        <li><a href="http://localhost:3000/blog" style="color: #0066cc; text-decoration: none;">Read our Blog</a></li>
                        <li><a href="http://localhost:3000" style="color: #0066cc; text-decoration: none;">Back to Homepage</a></li>
                    </ul>
                </div>
                
                <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                    Best regards,<br>
                    The Fleety Team
                </p>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        © 2025 Fleety. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
    </html>
    """
    
    payload = {
        "from": f"Fleety Support <{email_service.from_email}>",
        "to": email,
        "subject": "We've Received Your Inquiry - Fleety",
        "html": html_content
    }
    
    try:
        if email_service.enabled:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    email_service.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {email_service.api_key}"},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                logger.info(f"Confirmation email sent to {email}")
                return True
            else:
                logger.error(f"Failed to send confirmation email: {response.status_code}")
                return False
        else:
            logger.warning("Email service not configured - skipping confirmation email")
            return False
            
    except Exception as e:
        logger.error(f"Error sending confirmation email to {email}: {str(e)}")
        return False


async def send_admin_notification_email(inquiry_data: PublicContactCreate) -> bool:
    """Send notification email to admin/sales team"""
    
    admin_email = os.getenv("ADMIN_EMAIL", "admin@fleety.local")
    
    html_content = f"""
    <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="http://localhost:8000/public/FL_Logo.svg" alt="Fleety Logo" style="height: 50px; margin-bottom: 10px;">
                    <p style="color: #666; font-size: 12px; margin: 0; font-style: italic;">New Contact Inquiry</p>
                </div>
                
                <h1 style="color: #000; margin: 0 0 20px 0; font-size: 28px;">New Landing Page Inquiry</h1>
                
                <div style="background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #000; margin: 0 0 15px 0;">Inquiry Details:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; font-weight: bold; color: #333; width: 120px;">Name:</td>
                            <td style="padding: 10px; color: #555;">{inquiry_data.name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; font-weight: bold; color: #333;">Email:</td>
                            <td style="padding: 10px; color: #555;"><a href="mailto:{inquiry_data.email}" style="color: #0066cc; text-decoration: none;">{inquiry_data.email}</a></td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; font-weight: bold; color: #333;">Phone:</td>
                            <td style="padding: 10px; color: #555;">{inquiry_data.phone or 'Not provided'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 10px; font-weight: bold; color: #333;">Subject:</td>
                            <td style="padding: 10px; color: #555;">{inquiry_data.subject}</td>
                        </tr>
                    </table>
                </div>
                
                <h3 style="color: #000; margin: 20px 0 10px 0;">Message:</h3>
                <div style="background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <p style="color: #555; white-space: pre-wrap; margin: 0;">{inquiry_data.message}</p>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0;">
                    <p style="color: #856404; margin: 0; font-size: 14px;">
                        <strong>Consent:</strong> PDPA: {inquiry_data.agreeToPDPA} | Terms & Privacy: {inquiry_data.agreeToTermsAndPrivacy}
                    </p>
                </div>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        This is an automated notification. Please respond to the inquiry through your support system.
                    </p>
                </div>
            </div>
        </body>
    </html>
    """
    
    payload = {
        "from": f"Fleety System <{email_service.from_email}>",
        "to": admin_email,
        "subject": f"New Contact Inquiry from {inquiry_data.name}",
        "html": html_content
    }
    
    try:
        if email_service.enabled:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    email_service.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {email_service.api_key}"},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                logger.info(f"Admin notification sent to {admin_email}")
                return True
            else:
                logger.error(f"Failed to send admin notification: {response.status_code}")
                return False
        else:
            logger.warning("Email service not configured - skipping admin notification")
            return False
            
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")
        return False
