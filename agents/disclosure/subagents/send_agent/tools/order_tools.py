"""eDisclosures ordering tools for Send Agent.

Per Disclosure Desk SOP:
- Click on eFolder → eDisclosures button
- Select Generic Product and click Order eDisclosures
- Clear any mandatory audits before proceeding

API Flow:
1. Audit: POST /encompassdocs/v1/documentAudits/opening
2. Order: POST /encompassdocs/v1/documentOrders/opening
3. Deliver: POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
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
    order_initial_disclosure,
    audit_loan_for_disclosure,
    get_disclosure_orderer,
)

logger = logging.getLogger(__name__)


@tool
def audit_loan(loan_id: str, application_id: str = None) -> dict:
    """Run mandatory audit before ordering disclosures.
    
    This is Step 1 of the eDisclosures ordering process.
    Must pass audit before proceeding to order.
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Application ID (optional, will be fetched if not provided)
        
    Returns:
        Dictionary with:
        - success: Whether audit completed successfully
        - audit_id: Audit snapshot ID (needed for ordering)
        - has_issues: Whether audit found issues
        - issues: List of audit issues (if any)
        - blocking: Whether issues block ordering
    """
    logger.info(f"[ORDER] Running audit for loan {loan_id[:8]}...")
    
    try:
        orderer = get_disclosure_orderer()
        
        # Get application ID if not provided
        if application_id is None:
            application_id = orderer._get_application_id(loan_id)
            if application_id is None:
                return {
                    "success": False,
                    "error": "Could not get application ID from loan",
                    "blocking": True,
                }
        
        result = orderer.audit_loan(loan_id, application_id)
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"[ORDER] Audit error: {e}")
        return {
            "success": False,
            "error": str(e),
            "blocking": True,
        }


@tool
def order_disclosure_package(loan_id: str, dry_run: bool = True) -> dict:
    """Order Initial Disclosure package via eDisclosures API.
    
    Full flow:
    1. Audit loan (check for issues)
    2. Create document order
    3. Deliver to borrower (without fulfillment)
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only run audit without ordering
        
    Returns:
        Dictionary with:
        - success: Whether order completed successfully
        - tracking_id: Disclosure tracking ID
        - doc_set_id: Document set ID
        - audit_id: Audit snapshot ID
        - documents: List of documents in package
        - blocking: Whether any issues block ordering
    """
    logger.info(f"[ORDER] Ordering disclosure for loan {loan_id[:8]}... (dry_run={dry_run})")
    
    try:
        result = order_initial_disclosure(loan_id, dry_run=dry_run)
        
        if result.get("success"):
            logger.info(f"[ORDER] Success! Tracking ID: {result.get('tracking_id')}")
        else:
            logger.warning(f"[ORDER] Failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[ORDER] Order error: {e}")
        return {
            "success": False,
            "error": str(e),
            "blocking": True,
        }


@tool
def get_application_id(loan_id: str) -> dict:
    """Get the application ID for a loan.
    
    The application ID is required for the eDisclosures API.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with application_id
    """
    logger.info(f"[ORDER] Getting application ID for loan {loan_id[:8]}...")
    
    try:
        orderer = get_disclosure_orderer()
        app_id = orderer._get_application_id(loan_id)
        
        if app_id:
            return {
                "loan_id": loan_id,
                "application_id": app_id,
                "success": True,
            }
        else:
            return {
                "loan_id": loan_id,
                "error": "Application ID not found",
                "success": False,
            }
        
    except Exception as e:
        logger.error(f"[ORDER] Error getting application ID: {e}")
        return {
            "loan_id": loan_id,
            "error": str(e),
            "success": False,
        }


# Export tools for agent registration
order_tools = [
    audit_loan,
    order_disclosure_package,
    get_application_id,
]

