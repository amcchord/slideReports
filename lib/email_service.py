"""
Email service for sending reports via Postmark API.
"""
import requests
import base64
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Postmark"""
    
    def __init__(self, api_key: str):
        """
        Initialize email service.
        
        Args:
            api_key: Postmark API key
        """
        self.api_key = api_key
        self.from_email = "noreply@slide.recipes"
        self.postmark_url = "https://api.postmarkapp.com/email"
    
    def send_report_email(self, to_email: str, subject: str, 
                         text_body: Optional[str] = None,
                         html_body: Optional[str] = None,
                         pdf_content: Optional[bytes] = None,
                         pdf_filename: Optional[str] = None,
                         html_content: Optional[bytes] = None,
                         html_filename: Optional[str] = None) -> tuple[bool, str]:
        """
        Send email with PDF and/or HTML attachments via Postmark API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text_body: Optional plain text body for the email
            html_body: Optional HTML body for the email
            pdf_content: Optional PDF file as bytes
            pdf_filename: Optional filename for the PDF attachment
            html_content: Optional HTML file as bytes
            html_filename: Optional filename for the HTML attachment
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Default text body if none provided
        if text_body is None and html_body is None:
            text_body = "Please find your Slide backup report attached."
        
        # Prepare attachments list
        attachments = []
        
        if pdf_content is not None and pdf_filename is not None:
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            attachments.append({
                "Name": pdf_filename,
                "Content": pdf_base64,
                "ContentType": "application/pdf"
            })
        
        if html_content is not None and html_filename is not None:
            html_base64 = base64.b64encode(html_content).decode('utf-8')
            attachments.append({
                "Name": html_filename,
                "Content": html_base64,
                "ContentType": "text/html"
            })
        
        # Prepare Postmark API request
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": self.api_key
        }
        
        payload = {
            "From": self.from_email,
            "To": to_email,
            "Subject": subject,
        }
        
        # Add body (prefer HTML if available)
        if html_body is not None:
            payload["HtmlBody"] = html_body
            if text_body is not None:
                payload["TextBody"] = text_body
        else:
            if text_body is not None:
                payload["TextBody"] = text_body
        
        # Add attachments if any
        if attachments:
            payload["Attachments"] = attachments
        
        try:
            response = requests.post(self.postmark_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to_email}")
                return True, "Email sent successfully"
            else:
                error_msg = f"Failed to send email: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Exception sending email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

