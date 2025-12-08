"""Homeownership Counseling tools for preparation agent.

Implements G3: Homeownership Counseling agency validation.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.home_counseling import validate_agency_selection, get_housing_agencies

logger = logging.getLogger(__name__)


@tool
def validate_counseling_agency(loan_id: str) -> dict:
    """Validate homeownership counseling agency selection (G3 - CRITICAL).
    
    Per GAPS.md G3 and SOP Video Notes Lines 87-92:
    - Verify homeownership counseling agency has been selected
    - Agency info should be populated in loan
    
    Note: HUD API endpoint and field IDs are UNKNOWN - requires manual verification.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[G3] Validating counseling agency for loan {loan_id[:8]}...")
    
    result = validate_agency_selection(loan_id)
    
    if result.get("requires_manual_verification"):
        logger.warning("[G3] Manual verification required for counseling agency")
    
    return result


@tool
def search_counseling_agencies(zip_code: str, distance: int = 50) -> dict:
    """Search for HUD-approved counseling agencies near ZIP code (G3).
    
    Per GAPS.md G3:
    - Find agencies within distance of borrower ZIP code
    - Return list of approved agencies
    
    Note: HUD API endpoint not configured - placeholder for future implementation.
    
    Args:
        zip_code: ZIP code to search near
        distance: Search radius in miles (default: 50)
        
    Returns:
        Dictionary with agency search results
    """
    logger.info(f"[G3] Searching for counseling agencies near {zip_code}...")
    logger.warning("[G3] HUD API endpoint not configured - cannot search agencies automatically")
    
    agencies = get_housing_agencies(zip_code, distance)
    
    return {
        "gap_id": "G3",
        "gap_name": "Homeownership Counseling Agency Search",
        "status": "api_not_configured",
        "zip_code": zip_code,
        "distance": distance,
        "agencies_found": len(agencies),
        "agencies": agencies,
        "warnings": [
            "HUD API endpoint not configured - manual search required"
        ],
    }


# Export tools
counseling_tools = [
    validate_counseling_agency,
    search_counseling_agencies,
]

