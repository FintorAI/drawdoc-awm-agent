"""ATR/QM tools for Send Agent.

Per Disclosure Desk SOP:
- Go to Forms → ATR/QM Management → Qualification → Points and Fees
- ATR/QM Eligibility: Flags must NOT be RED to proceed
- This is MANDATORY before ordering disclosures
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
    check_atr_qm_flags,
    get_points_fees_status,
    get_atr_qm_checker,
    FlagStatus,
)

logger = logging.getLogger(__name__)


@tool
def check_atr_qm(loan_id: str) -> dict:
    """Check ATR/QM flags for a loan.
    
    Per SOP: All flags must NOT be RED to proceed.
    This is MANDATORY before ordering disclosures.
    
    Checks:
    - Loan Features Flag
    - Points and Fees Limit Flag
    - Price Limit Flag
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - passed: Whether all flags are acceptable (not RED)
        - loan_features_flag: Status of Loan Features flag
        - points_fees_flag: Status of Points and Fees flag
        - price_limit_flag: Status of Price Limit flag
        - red_flags: List of flags that are RED (blocking)
        - yellow_flags: List of flags that are YELLOW (warning)
        - blocking: Whether red flags block disclosure
        - action: Recommended action
    """
    logger.info(f"[ATR/QM] Checking flags for loan {loan_id[:8]}...")
    
    try:
        result = check_atr_qm_flags(loan_id)
        
        if result.get("passed"):
            logger.info("[ATR/QM] All flags acceptable")
        else:
            logger.warning(f"[ATR/QM] Red flags: {result.get('red_flags')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[ATR/QM] Error checking flags: {e}")
        return {
            "passed": False,
            "error": str(e),
            "blocking": True,
            "action": "Error checking ATR/QM flags - contact support"
        }


@tool
def get_points_and_fees_test(loan_id: str) -> dict:
    """Get Points & Fees test status for a loan.
    
    The Points & Fees test is part of QM eligibility.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - flag: Points & Fees flag status
        - limit: Points & Fees limit amount
        - actual: Actual Points & Fees amount
        - passed: Whether test passed
    """
    logger.info(f"[ATR/QM] Getting Points & Fees status for loan {loan_id[:8]}...")
    
    try:
        result = get_points_fees_status(loan_id)
        
        return {
            "loan_id": loan_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"[ATR/QM] Error getting Points & Fees: {e}")
        return {
            "loan_id": loan_id,
            "error": str(e),
            "passed": False,
        }


# Export tools for agent registration
atr_qm_tools = [
    check_atr_qm,
    get_points_and_fees_test,
]

