"""eFolder configuration tools for preparation agent.

Implements G20: eFolder product selection based on LTV.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.encompass_client import get_encompass_client

logger = logging.getLogger(__name__)


@tool
def configure_efolder_products(loan_id: str, dry_run: bool = False) -> dict:
    """Configure eFolder product selection based on LTV (G20 - LOW).
    
    Per GAPS.md G20 and SOP Video Notes Lines 229-231:
    - If LTV < 80%, uncheck PMI Disclosure
    - Configure eFolder product selections
    
    If LTV < 80%, uncheck PMI Disclosure (field UNKNOWN - logs warning).
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, simulate operation without making changes
        
    Returns:
        Dictionary with eFolder configuration results
    """
    logger.info(f"[G20] Configuring eFolder products for loan {loan_id[:8]}...")
    logger.warning("[G20] PMI Disclosure checkbox field ID UNKNOWN - requires manual verification")
    
    try:
        client = get_encompass_client()
        
        # Get LTV value (field 353)
        loan_data = client.get_loan_fields(loan_id, ["353"])
        ltv = loan_data.get("353")
        
        if ltv is None:
            logger.warning("[G20] LTV value not found (field 353)")
            return {
                "gap_id": "G20",
                "gap_name": "eFolder Product Selection",
                "status": "ltv_not_found",
                "error": "LTV value not found in loan (field 353)",
            }
        
        ltv_value = float(ltv)
        logger.info(f"[G20] LTV: {ltv_value}%")
        
        # Determine if PMI Disclosure should be unchecked
        uncheck_pmi = ltv_value < 80
        
        if dry_run:
            logger.info(f"[G20] DRY RUN - LTV: {ltv_value}%, PMI Disclosure: {'uncheck' if uncheck_pmi else 'leave checked'}")
            return {
                "gap_id": "G20",
                "gap_name": "eFolder Product Selection",
                "status": "dry_run",
                "ltv": ltv_value,
                "pmi_disclosure_action": "uncheck" if uncheck_pmi else "leave_checked",
                "message": "Dry run - no changes made",
            }
        
        result = {
            "gap_id": "G20",
            "gap_name": "eFolder Product Selection",
            "status": "manual_verification_required",
            "ltv": ltv_value,
            "pmi_disclosure_action": "uncheck" if uncheck_pmi else "leave_checked",
            "warnings": [
                "PMI Disclosure checkbox field ID UNKNOWN - manual verification required"
            ],
            "requires_manual_verification": True,
        }
        
        if uncheck_pmi:
            result["message"] = f"LTV is {ltv_value}% (< 80%) - Please manually uncheck PMI Disclosure in eFolder"
            logger.warning(f"[G20] LTV < 80% - PMI Disclosure should be unchecked")
        else:
            result["message"] = f"LTV is {ltv_value}% (>= 80%) - PMI Disclosure should remain checked"
            logger.info(f"[G20] LTV >= 80% - PMI Disclosure OK as is")
        
        return result
        
    except Exception as e:
        logger.error(f"[G20] Error configuring eFolder products: {e}")
        return {
            "gap_id": "G20",
            "gap_name": "eFolder Product Selection",
            "status": "error",
            "error": str(e),
        }


# Export tools
efolder_tools = [
    configure_efolder_products,
]

