"""Itemization validation tools for preparation agent.

Implements G5: 2015 Itemization validations.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.itemization_validator import validate_itemization

logger = logging.getLogger(__name__)


@tool
def validate_itemization_requirements(loan_id: str, loan_purpose: str = "Purchase") -> dict:
    """Validate 2015 Itemization requirements (G5 - CRITICAL).
    
    Per GAPS.md G5 and SOP Video Notes Lines 180-195:
    - Itemize fees when printing checkbox (UNKNOWN field ID)
    - Bona Fide checkbox (NEWHUD.X1067)
    - Mandatory fees based on loan purpose:
      - All loans: Appraisal Fee, Credit Report Fee
      - Purchase: Title Settlement, Lender Title Insurance, Owner Title Insurance
      - Refinance: Title Settlement, Lender Title Insurance, Recording Fee
    
    Args:
        loan_id: Encompass loan GUID
        loan_purpose: Loan purpose (Purchase/Refinance)
        
    Returns:
        Dictionary with itemization validation results
    """
    logger.info(f"[G5] Validating itemization for loan {loan_id[:8]} ({loan_purpose})...")
    
    try:
        result = validate_itemization(loan_id, loan_purpose)
        
        return {
            "gap_id": "G5",
            "gap_name": "2015 Itemization Validations",
            "status": "checked" if result.all_valid else "incomplete",
            "all_valid": result.all_valid,
            "loan_purpose": result.loan_purpose,
            "checkboxes_checked": result.checkboxes_checked,
            "checkboxes_missing": result.checkboxes_missing,
            "fees_present": result.fees_present,
            "fees_missing": result.fees_missing,
            "warnings": result.warnings,
            "requires_manual_verification": True,
        }
    
    except Exception as e:
        logger.error(f"[G5] Error validating itemization: {e}")
        return {
            "gap_id": "G5",
            "gap_name": "2015 Itemization Validations",
            "status": "error",
            "error": str(e),
        }


# Export tools
itemization_tools = [
    validate_itemization_requirements,
]

