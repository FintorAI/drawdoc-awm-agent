"""Home Counseling Agency Integration (G3 - CRITICAL).

Implements homeownership counseling agency validation and HUD API integration.

Per SOP Video Notes Lines 87-92:
- Verify homeownership counseling agency selected
- Agencies must be HUD-approved

Note: HUD API endpoint is UNKNOWN - placeholder implementation with logging.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from packages.shared.encompass_client import get_encompass_client

logger = logging.getLogger(__name__)


@dataclass
class Agency:
    """Homeownership counseling agency."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    distance: Optional[float] = None
    approved: bool = True


def get_housing_agencies(zip_code: str, distance: int = 50) -> List[Agency]:
    """Fetch HUD-approved housing counseling agencies near ZIP code.
    
    Note: HUD API endpoint UNKNOWN - logs warning for manual selection.
    
    Args:
        zip_code: ZIP code to search near
        distance: Search radius in miles (default: 50)
        
    Returns:
        List of Agency objects (empty list until API configured)
    """
    logger.warning("[G3] HUD API endpoint not configured - requires manual agency selection")
    logger.info(f"[G3] Would search for agencies near {zip_code} within {distance} miles")
    
    # TODO: Implement HUD API integration when endpoint is available
    # Placeholder for HUD Housing Counseling API:
    # - Endpoint: TBD (check HUD.gov or CFPB resources)
    # - Authentication: TBD
    # - Response: List of approved agencies with contact info
    
    return []


def validate_agency_selection(loan_id: str) -> Dict:
    """Validate that a homeownership counseling agency has been selected.
    
    Note: Field IDs for agency selection are UNKNOWN - logs warning.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[G3] Validating counseling agency for loan {loan_id[:8]}...")
    logger.warning("[G3] Agency selection field IDs UNKNOWN - requires manual verification in Encompass")
    
    # Potential field IDs to check (need verification):
    # - Agency Name field
    # - Agency Phone field
    # - Agency Address field
    # - Agency Selection Checkbox
    
    return {
        "gap_id": "G3",
        "gap_name": "Homeownership Counseling Agency",
        "status": "manual_verification_required",
        "message": "Please manually verify homeownership counseling agency selected in Encompass",
        "warnings": [
            "HUD API endpoint not configured - cannot search agencies automatically",
            "Agency selection field IDs UNKNOWN - manual verification required"
        ],
        "requires_manual_verification": True,
    }


def check_agency_fields(client, loan_id: str) -> Dict:
    """Check if agency-related fields are populated.
    
    Attempts to read common agency field IDs (if known).
    
    Args:
        client: EncompassClient instance
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with field check results
    """
    logger.info(f"[G3] Checking agency fields for loan {loan_id[:8]}...")
    
    # Common fields that might exist (need verification):
    # These are guesses - actual field IDs need to be mapped
    possible_fields = []
    
    if not possible_fields:
        logger.warning("[G3] No agency field IDs configured - cannot check fields")
        return {
            "status": "no_fields_configured",
            "message": "Agency field IDs not mapped",
        }
    
    try:
        loan_data = client.get_loan_fields(loan_id, possible_fields)
        
        return {
            "status": "checked",
            "fields": loan_data,
        }
    except Exception as e:
        logger.error(f"[G3] Error checking agency fields: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
