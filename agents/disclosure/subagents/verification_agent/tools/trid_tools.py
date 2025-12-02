"""TRID compliance tools for disclosure verification agent.

Per Disclosure Desk SOP (v2):
- Check Application Date and LE Due Date
- Check if "Send Initial Disclosures" alert exists
- Check lock status (locked vs non-locked flow)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared import (
    check_trid_compliance,
    check_lock_status,
    get_trid_checker,
)

logger = logging.getLogger(__name__)


@tool
def check_trid_dates(loan_id: str) -> dict:
    """Check TRID compliance dates for Initial LE disclosure.
    
    Per SOP: LE must be sent within 3 business days of Application Date.
    Business days exclude Sundays and federal holidays.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - compliant: Whether dates are compliant
        - application_date: Application date (ISO format)
        - le_due_date: LE due date (ISO format)
        - days_remaining: Days until LE due date
        - is_past_due: Whether LE due date has passed
        - action: Recommended action if non-compliant
        - blocking: Whether this blocks disclosure
    """
    logger.info(f"[TRID] Checking TRID dates for loan {loan_id[:8]}...")
    
    try:
        result = check_trid_compliance(loan_id)
        
        if result.get("is_past_due"):
            logger.warning(f"[TRID] LE Due Date PASSED - escalate to supervisor")
        elif result.get("compliant"):
            logger.info(f"[TRID] TRID compliant - {result.get('days_remaining', 0)} days remaining")
        else:
            logger.warning(f"[TRID] TRID not compliant: {result.get('action')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRID] Error checking TRID dates: {e}")
        return {
            "compliant": False,
            "error": str(e),
            "blocking": True,
            "action": "Error checking TRID compliance - see error details"
        }


@tool
def check_disclosure_alert_exists(loan_id: str) -> dict:
    """Check if "Send Initial Disclosures" alert exists.
    
    Per SOP: Under Alerts & Messages tab, there must be an alert titled
    "Send Initial Disclosures" if the initial disclosure has not been issued yet.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with alert status
    """
    logger.info(f"[TRID] Checking disclosure alert for loan {loan_id[:8]}...")
    
    try:
        checker = get_trid_checker()
        alert_exists = checker.check_disclosure_alert(loan_id)
        
        return {
            "alert_exists": alert_exists,
            "success": True,
            "message": "Send Initial Disclosures alert found" if alert_exists else "Alert not found"
        }
        
    except Exception as e:
        logger.error(f"[TRID] Error checking alert: {e}")
        return {
            "alert_exists": False,
            "success": False,
            "error": str(e)
        }


@tool
def check_rate_lock_status(loan_id: str) -> dict:
    """Check rate lock status for the loan.
    
    Per SOP:
    - Case 1 (Locked Loans): All TRID info must be updated
    - Case 2 (Non-Locked Loans): Monitor App Date & LE Due Date
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - is_locked: Whether rate is locked
        - lock_date: Lock date (if locked)
        - lock_expiration: Lock expiration date
        - flow: "locked" or "non_locked"
    """
    logger.info(f"[TRID] Checking lock status for loan {loan_id[:8]}...")
    
    try:
        result = check_lock_status(loan_id)
        
        # Add flow indicator
        result["flow"] = "locked" if result.get("is_locked") else "non_locked"
        
        if result.get("is_locked"):
            logger.info(f"[TRID] Loan is LOCKED - using locked flow")
        else:
            logger.info(f"[TRID] Loan is NOT LOCKED - using non-locked flow")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRID] Error checking lock status: {e}")
        return {
            "is_locked": False,
            "flow": "non_locked",
            "error": str(e)
        }


# Export tools for agent registration
trid_tools = [
    check_trid_dates,
    check_disclosure_alert_exists,
    check_rate_lock_status,
]

