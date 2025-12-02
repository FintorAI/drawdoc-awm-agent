"""RegZ-LE form tools for disclosure preparation agent.

Per Disclosure Desk SOP (v2):
- Update LE Date Issued = Current Date
- Set Interest Accrual to 360/360
- Apply Late Charge rules per loan type
- Set Assumption text per loan type
- Handle Buydown and Prepayment fields
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
    update_regz_le_form,
    get_late_charge,
    get_assumption_text,
    get_regz_le_updater,
)

logger = logging.getLogger(__name__)


@tool
def update_regz_le_fields(loan_id: str, dry_run: bool = True) -> dict:
    """Update RegZ-LE form fields per SOP requirements.
    
    Updates:
    - LE Date Issued = Current Date
    - Interest Accrual = 360/360
    - Late Charge: Conventional 15d/5%, FHA/VA 15d/4%, NC 4% all
    - Assumption: Conventional "may not", FHA/VA "may, subject to conditions"
    - Buydown fields (if marked)
    - Prepayment fields
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only calculate updates without writing
        
    Returns:
        Dictionary with:
        - success: Whether update succeeded
        - updates_made: Dictionary of field updates
        - errors: List of any errors
        - warnings: List of any warnings (e.g., missing buydown fields)
    """
    logger.info(f"[REGZ-LE] Updating form for loan {loan_id[:8]}... (dry_run={dry_run})")
    
    try:
        result = update_regz_le_form(loan_id, dry_run=dry_run)
        
        if result.get("success"):
            logger.info(f"[REGZ-LE] Updated {len(result.get('updates_made', {}))} fields")
        else:
            logger.warning(f"[REGZ-LE] Update issues: {result.get('errors')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[REGZ-LE] Error updating form: {e}")
        return {
            "success": False,
            "error": str(e),
            "updates_made": {},
        }


@tool
def get_late_charge_values(loan_type: str, property_state: str = "") -> dict:
    """Get late charge values for a loan type and state.
    
    Per SOP:
    - Conventional: 15 days, 5%
    - FHA/VA: 15 days, 4%
    - North Carolina: 4% for ALL loan types
    
    Args:
        loan_type: Loan type (Conventional, FHA, VA, USDA)
        property_state: State abbreviation (for NC override)
        
    Returns:
        Dictionary with days and percentage
    """
    logger.info(f"[REGZ-LE] Getting late charge for {loan_type}, {property_state}")
    
    result = get_late_charge(loan_type, property_state)
    
    logger.info(f"[REGZ-LE] Late charge: {result.get('days')} days, {result.get('percent')}%")
    
    return {
        "loan_type": loan_type,
        "property_state": property_state,
        "days": result.get("days"),
        "percent": result.get("percent"),
    }


@tool
def get_assumption_clause(loan_type: str) -> dict:
    """Get assumption text for a loan type.
    
    Per SOP:
    - Conventional: "may not"
    - FHA/VA: "may, subject to conditions"
    
    Args:
        loan_type: Loan type
        
    Returns:
        Dictionary with assumption text
    """
    text = get_assumption_text(loan_type)
    
    return {
        "loan_type": loan_type,
        "assumption_text": text,
        "message": f"Assumption: This loan {text} be assumed."
    }


# Export tools for agent registration
regz_le_tools = [
    update_regz_le_fields,
    get_late_charge_values,
    get_assumption_clause,
]

