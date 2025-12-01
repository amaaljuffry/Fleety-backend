import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ResendEmailService:
    """Async email service using Resend API for transactional emails"""
    
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.api_url = "https://api.resend.com/emails"
        self.from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Resend API key not configured - email sending disabled")
    
    async def send_waitlist_confirmation(self, email: str, name: str) -> bool:
        """Send waitlist confirmation email via Resend API"""
        if not self.enabled:
            logger.warning(f"Email sending disabled, skipping confirmation for {email}")
            return False
        
        html_content = f"""
        <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <img src="http://localhost:8000/public/FL_Logo.svg" alt="Fleety Logo" style="height: 50px; margin-bottom: 10px;">
                        <p style="color: #666; font-size: 12px; margin: 0; font-style: italic;">Smarter Fleet Management for SMEs & Logistics</p>
                    </div>
                    
                    <h1 style="color: #000; margin: 0 0 20px 0; font-size: 28px;">Fleety is Live! 🚀</h1>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hey {name},
                    </p>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Thank you for joining the Fleety waitlist! We're excited to have you on board. 
                    </p>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        You're now part of an exclusive group getting early access to Fleety when we launch. 
                        We'll keep you updated on our progress and send you exclusive perks along the way.
                    </p>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                        Stay tuned!
                    </p>
                    
                    <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            © 2025 Fleety. All rights reserved.<br>
                            <a href="http://localhost:3000" style="color: #999; text-decoration: none;">fleety.local</a>
                        </p>
                        <p style="color: #bbb; font-size: 11px; margin-top: 10px; margin-bottom: 0;">
                            <a href="http://localhost:8000/api/waitlist/unsubscribe?email={email}" style="color: #bbb; text-decoration: none;">Unsubscribe from emails</a>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        payload = {
            "from": f"Fleety <{self.from_email}>",
            "to": email,
            "subject": "Welcome to the Fleety Waitlist!",
            "html": html_content
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                logger.info(f"Waitlist confirmation sent to {email}")
                return True
            else:
                logger.error(f"Resend API error ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send waitlist confirmation to {email}: {str(e)}")
            return False
    
    async def send_launch_notification(self, email: str, name: str) -> bool:
        """Send launch notification email"""
        if not self.enabled:
            logger.warning(f"Email sending disabled, skipping launch notification for {email}")
            return False
        
        launch_url = os.getenv("LAUNCH_URL", "http://localhost:3000")
        
        html_content = f"""
        <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <img src="http://localhost:8000/public/FL_Logo.svg" alt="Fleety Logo" style="height: 50px; margin-bottom: 10px;">
                        <p style="color: #666; font-size: 12px; margin: 0; font-style: italic;">Smarter Fleet Management for SMEs & Logistics</p>
                    </div>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        Hey {name},
                    </p>
                    
                    <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                        The wait is over! Fleety is now officially live, and as an early supporter, 
                        you get exclusive early access.
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{launch_url}" style="background-color: #000; color: white; padding: 14px 40px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 16px;">
                            Get Started Now
                        </a>
                    </div>
                    
                    <p style="color: #555; font-size: 14px; line-height: 1.6; margin: 0;">
                        Thank you for being part of this journey!
                    </p>
                    
                    <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                        <p style="color: #999; font-size: 12px; margin: 0;">
                            © 2025 Fleety. All rights reserved.<br>
                            <a href="http://localhost:3000" style="color: #999; text-decoration: none;">fleety.local</a>
                        </p>
                        <p style="color: #bbb; font-size: 11px; margin-top: 10px;">
                            <a href="http://localhost:8000/api/waitlist/unsubscribe?email={email}" style="color: #bbb; text-decoration: none;">Unsubscribe from emails</a>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        payload = {
            "from": f"Fleety <{self.from_email}>",
            "to": email,
            "subject": "Fleety is Live - Your Early Access Awaits!",
            "html": html_content
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                logger.info(f"Launch notification sent to {email}")
                return True
            else:
                logger.error(f"Resend API error ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send launch notification to {email}: {str(e)}")
            return False
    
    async def send_bulk_update(self, emails: list, subject: str, html: str) -> dict:
        """Send bulk update emails to multiple recipients"""
        if not self.enabled:
            logger.warning("Email sending disabled, skipping bulk update")
            return {"sent": 0, "failed": 0, "errors": []}
        
        sent = 0
        failed = 0
        errors = []
        
        try:
            async with httpx.AsyncClient() as client:
                for email in emails:
                    try:
                        payload = {
                            "from": f"Fleety <{self.from_email}>",
                            "to": email,
                            "subject": subject,
                            "html": html
                        }
                        
                        response = await client.post(
                            self.api_url,
                            json=payload,
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            sent += 1
                        else:
                            failed += 1
                            errors.append({"email": email, "error": response.text})
                            
                    except Exception as e:
                        failed += 1
                        errors.append({"email": email, "error": str(e)})
                
                logger.info(f"Bulk email sent: {sent} successful, {failed} failed")
                
        except Exception as e:
            logger.error(f"Bulk email sending failed: {str(e)}")
            errors.append({"error": str(e)})
        
        return {"sent": sent, "failed": failed, "errors": errors}


# Instantiate global service
resend_service = ResendEmailService()


def send_support_email(
    customer_name: str,
    customer_email: str,
    inquiry: str,
    ticket_id: str
):
    """
    Send support ticket email to admin
    """
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", sender_email)
    
    if not sender_email or not sender_password:
        raise Exception("Email configuration missing in environment variables")
    
    # Create message for admin
    admin_msg = MIMEMultipart("alternative")
    admin_msg["Subject"] = f"New Support Ticket #{ticket_id}"
    admin_msg["From"] = sender_email
    admin_msg["To"] = admin_email
    
    admin_text = f"""
New Support Ticket Received

Ticket ID: {ticket_id}
Customer Name: {customer_name}
Customer Email: {customer_email}

Inquiry:
{inquiry}

Please log in to the admin dashboard to respond to this ticket.
    """
    
    admin_html = f"""
<html>
  <body>
    <h2>New Support Ticket Received</h2>
    <p><strong>Ticket ID:</strong> {ticket_id}</p>
    <p><strong>Customer Name:</strong> {customer_name}</p>
    <p><strong>Customer Email:</strong> {customer_email}</p>
    <p><strong>Inquiry:</strong></p>
    <p>{inquiry.replace(chr(10), '<br>')}</p>
    <p>Please log in to the admin dashboard to respond to this ticket.</p>
  </body>
</html>
    """
    
    admin_msg.attach(MIMEText(admin_text, "plain"))
    admin_msg.attach(MIMEText(admin_html, "html"))
    
    # Create message for customer
    customer_msg = MIMEMultipart("alternative")
    customer_msg["Subject"] = "We received your support inquiry"
    customer_msg["From"] = sender_email
    customer_msg["To"] = customer_email
    
    customer_text = f"""
Hello {customer_name},

Thank you for reaching out to us. We have received your inquiry and a member of our support team will get back to you shortly.

Your Ticket ID: {ticket_id}

Your Inquiry:
{inquiry}

We appreciate your patience.

Best regards,
Fleety Support Team
    """
    
    customer_html = f"""
<html>
  <body>
    <h2>Thank you for contacting Fleety!</h2>
    <p>Hello {customer_name},</p>
    <p>We have received your inquiry and a member of our support team will get back to you shortly.</p>
    <p><strong>Your Ticket ID:</strong> {ticket_id}</p>
    <p><strong>Your Inquiry:</strong></p>
    <p>{inquiry.replace(chr(10), '<br>')}</p>
    <p>We appreciate your patience.</p>
    <p>Best regards,<br>Fleety Support Team</p>
  </body>
</html>
    """
    
    customer_msg.attach(MIMEText(customer_text, "plain"))
    customer_msg.attach(MIMEText(customer_html, "html"))
    
    # Send emails
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            
            # Send to admin
            server.send_message(admin_msg)
            
            # Send to customer
            server.send_message(customer_msg)
            
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise


def send_password_reset_email(
    user_email: str,
    user_name: str,
    reset_token: str
):
    """
    Send password reset email to user
    """
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        raise Exception("Email configuration missing in environment variables")
    
    # Build reset link (adjust domain as needed)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8081")
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your Fleety Password"
    msg["From"] = sender_email
    msg["To"] = user_email
    
    text = f"""
Hello {user_name},

You requested to reset your Fleety password. Click the link below to reset it:

{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
Fleety Team
    """
    
    html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #111;">Reset Your Password</h2>
      <p>Hello {user_name},</p>
      <p>You requested to reset your Fleety password. Click the button below to reset it:</p>
      
      <div style="text-align: center; margin: 30px 0;">
        <a href="{reset_link}" style="background-color: #000; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
          Reset Password
        </a>
      </div>
      
      <p style="font-size: 12px; color: #666;">
        Or copy and paste this link in your browser:<br>
        <span style="word-break: break-all;">{reset_link}</span>
      </p>
      
      <p style="font-size: 12px; color: #999;">
        This link will expire in 1 hour.
      </p>
      
      <p style="font-size: 12px; color: #666; margin-top: 20px;">
        If you didn't request this, please ignore this email.
      </p>
      
      <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
      <p style="font-size: 12px; color: #999;">© 2025 Fleety. All rights reserved.</p>
    </div>
  </body>
</html>
    """
    
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
        raise
