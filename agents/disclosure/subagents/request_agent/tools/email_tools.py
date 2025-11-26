"""Email tools for disclosure request agent.

NOTE: Email service provider is TBD. This implementation includes a placeholder
that can be easily swapped for SMTP, SendGrid, AWS SES, etc.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)


def _send_email_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP (placeholder implementation).
    
    TODO: Implement actual SMTP sending when email service is chosen.
    Environment variables needed:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USERNAME
    - SMTP_PASSWORD
    - EMAIL_FROM
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("EMAIL_FROM", "noreply@example.com")
        
        if not smtp_username or not smtp_password:
            logger.warning("[EMAIL] SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"[EMAIL] Sent via SMTP to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"[EMAIL] SMTP error: {e}")
        return False


def _send_email_via_sendgrid(to_email: str, subject: str, body: str) -> bool:
    """Send email via SendGrid API (placeholder implementation).
    
    TODO: Implement when SendGrid is chosen.
    Environment variables needed:
    - SENDGRID_API_KEY
    - EMAIL_FROM
    """
    logger.info(f"[EMAIL] SendGrid not configured")
    return False


def _send_email_via_aws_ses(to_email: str, subject: str, body: str) -> bool:
    """Send email via AWS SES (placeholder implementation).
    
    TODO: Implement when AWS SES is chosen.
    Environment variables needed:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION
    - EMAIL_FROM
    """
    logger.info(f"[EMAIL] AWS SES not configured")
    return False


@tool
def send_disclosure_email(
    loan_id: str,
    lo_email: str,
    fields_status: dict,
    dry_run: bool = True
) -> dict:
    """Send email to LO notifying them to review disclosure fields.
    
    Email includes:
    - Loan ID
    - Summary of field status (populated, missing, cleaned)
    - Link to Encompass loan (if applicable)
    - Instructions for next steps
    
    Args:
        loan_id: Encompass loan GUID
        lo_email: Loan officer email address
        fields_status: Dictionary with verification and preparation results
        dry_run: If True, don't actually send email (default: True)
        
    Returns:
        Dictionary with email send status
    """
    logger.info(f"[EMAIL] {'[DRY RUN] ' if dry_run else ''}Sending disclosure email to {lo_email}...")
    
    # Extract status information
    fields_checked = fields_status.get('fields_checked', 0)
    fields_missing = len(fields_status.get('fields_missing', []))
    fields_populated = len(fields_status.get('fields_populated', []))
    fields_cleaned = len(fields_status.get('fields_cleaned', []))
    
    # Compose email
    subject = f"Disclosure Ready for Review - Loan {loan_id[:8]}"
    
    body = f"""Hello,

The disclosure fields for loan {loan_id} have been prepared and are ready for your review.

FIELD STATUS SUMMARY:
- Total fields checked: {fields_checked}
- Fields missing values: {fields_missing}
- Fields populated by prep agent: {fields_populated}
- Fields cleaned/normalized: {fields_cleaned}

{"⚠️ WARNING: Some fields are still missing values. Please review and complete before proceeding." if fields_missing > 0 else "✓ All required fields have values."}

NEXT STEPS:
1. Review the loan in Encompass: {loan_id}
2. Verify all field values are correct
3. Complete any remaining missing fields
4. Proceed with disclosure generation

Thank you,
Disclosure Automation System

---
This is an automated message. Please do not reply to this email.
"""
    
    if dry_run:
        logger.info("[EMAIL] [DRY RUN] Would send email:")
        logger.info(f"  To: {lo_email}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Body length: {len(body)} characters")
        
        return {
            "loan_id": loan_id,
            "lo_email": lo_email,
            "dry_run": True,
            "message": "[DRY RUN] Email not actually sent",
            "email_subject": subject,
            "email_body": body,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
    
    # Determine email service to use
    email_service = os.getenv("EMAIL_SERVICE", "smtp").lower()
    
    success = False
    if email_service == "smtp":
        success = _send_email_via_smtp(lo_email, subject, body)
    elif email_service == "sendgrid":
        success = _send_email_via_sendgrid(lo_email, subject, body)
    elif email_service == "aws_ses":
        success = _send_email_via_aws_ses(lo_email, subject, body)
    else:
        logger.error(f"[EMAIL] Unknown email service: {email_service}")
        return {
            "loan_id": loan_id,
            "lo_email": lo_email,
            "error": f"Unknown email service: {email_service}",
            "success": False
        }
    
    if success:
        logger.info(f"[EMAIL] Successfully sent to {lo_email}")
        return {
            "loan_id": loan_id,
            "lo_email": lo_email,
            "email_sent": True,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
    else:
        logger.error(f"[EMAIL] Failed to send to {lo_email}")
        return {
            "loan_id": loan_id,
            "lo_email": lo_email,
            "error": "Email sending failed",
            "success": False
        }


@tool
def get_lo_contact_info(loan_id: str) -> dict:
    """Get loan officer contact information from Encompass.
    
    Use this to automatically find the LO's email if not provided.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with LO name and email
    """
    logger.info(f"[GET_LO] Getting LO info for loan {loan_id[:8]}...")
    
    # TODO: Implement actual Encompass field lookup
    # Common LO email fields: "Loan Officer Email", "LO Email", etc.
    
    from packages.shared import get_encompass_client
    
    try:
        encompass = get_encompass_client()
        
        # Try common LO email field IDs
        lo_email_field_ids = ["LO.Email", "LoanOfficerEmail", "360"]  # 360 is common
        
        for field_id in lo_email_field_ids:
            try:
                email = encompass.get_field_value(loan_id, field_id)
                if email and "@" in str(email):
                    logger.info(f"[GET_LO] Found LO email in field {field_id}: {email}")
                    return {
                        "loan_id": loan_id,
                        "lo_email": email,
                        "field_id": field_id,
                        "success": True
                    }
            except:
                continue
        
        logger.warning(f"[GET_LO] No LO email found for loan {loan_id[:8]}")
        return {
            "loan_id": loan_id,
            "error": "LO email not found",
            "success": False
        }
        
    except Exception as e:
        logger.error(f"[GET_LO] Error: {e}")
        return {
            "loan_id": loan_id,
            "error": str(e),
            "success": False
        }

