"""Cash to Close tools for disclosure preparation agent.

Per Disclosure Desk SOP (v2):
- Match CTC with Estimated Cash to Close on LE page 2
- Purchase: Check specific boxes
- Refinance: Check Alternative form checkbox
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
    match_cash_to_close,
    get_ctc_settings,
    get_ctc_matcher,
)

logger = logging.getLogger(__name__)


@tool
def match_ctc(loan_id: str, dry_run: bool = True) -> dict:
    """Match Cash to Close per SOP requirements.
    
    Per SOP:
    - Purchase: Check 'Use Actual Down Payment & Closing Costs Financed'
               & 'Include Payoffs in Adjustments'
    - Refinance: Check 'Alternative form checkbox'
    - Verify calculated CTC matches displayed CTC
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only calculate without writing
        
    Returns:
        Dictionary with:
        - success: Whether operation succeeded
        - matched: Whether CTC values match
        - loan_purpose: Purchase or Refinance
        - calculated_ctc: Calculated Cash to Close amount
        - displayed_ctc: Displayed CTC on LE page 2
        - difference: Difference between calculated and displayed
        - updates_made: Settings that were applied
        - blocking: Whether mismatch blocks disclosure
    """
    logger.info(f"[CTC] Matching Cash to Close for loan {loan_id[:8]}... (dry_run={dry_run})")
    
    try:
        result = match_cash_to_close(loan_id, dry_run=dry_run)
        
        if result.get("matched"):
            logger.info(f"[CTC] Match verified: ${result.get('calculated_ctc', 0):,.2f}")
        else:
            logger.warning(f"[CTC] Mismatch: Calculated=${result.get('calculated_ctc', 0):,.2f}, "
                          f"Displayed=${result.get('displayed_ctc', 0):,.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"[CTC] Error matching CTC: {e}")
        return {
            "success": False,
            "matched": False,
            "error": str(e),
            "blocking": True,
        }


@tool
def get_ctc_checkbox_settings(loan_purpose: str) -> dict:
    """Get CTC checkbox settings for a loan purpose.
    
    Per SOP:
    - Purchase: Check specific boxes
    - Refinance: Check Alternative form checkbox
    
    Args:
        loan_purpose: Loan purpose (Purchase, Refinance, etc.)
        
    Returns:
        Dictionary with field settings to apply
    """
    logger.info(f"[CTC] Getting CTC settings for {loan_purpose}")
    
    settings = get_ctc_settings(loan_purpose)
    
    return {
        "loan_purpose": loan_purpose,
        "settings": settings,
        "field_count": len(settings),
        "description": f"Apply {len(settings)} checkbox settings for {loan_purpose}"
    }


@tool
def verify_ctc_match(loan_id: str) -> dict:
    """Verify that calculated CTC matches displayed CTC.
    
    This is a read-only check - does not apply any settings.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with verification result
    """
    logger.info(f"[CTC] Verifying CTC match for loan {loan_id[:8]}...")
    
    try:
        matcher = get_ctc_matcher()
        
        # Get CTC values
        calculated = matcher._get_calculated_ctc(loan_id)
        displayed = matcher._get_displayed_ctc(loan_id)
        
        if calculated is None or displayed is None:
            return {
                "verified": False,
                "calculated_ctc": calculated,
                "displayed_ctc": displayed,
                "error": "One or both CTC values not available",
                "blocking": True,
            }
        
        difference = abs(calculated - displayed)
        matched = difference <= 0.01  # Allow penny rounding
        
        return {
            "verified": matched,
            "calculated_ctc": calculated,
            "displayed_ctc": displayed,
            "difference": difference,
            "blocking": not matched,
        }
        
    except Exception as e:
        logger.error(f"[CTC] Error verifying CTC: {e}")
        return {
            "verified": False,
            "error": str(e),
            "blocking": True,
        }


# Export tools for agent registration
ctc_tools = [
    match_ctc,
    get_ctc_checkbox_settings,
    verify_ctc_match,
]

