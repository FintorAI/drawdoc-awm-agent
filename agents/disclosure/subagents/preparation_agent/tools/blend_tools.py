"""Blend integration tools for preparation agent.

Implements G19: Blend ORGID check.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared import read_field

logger = logging.getLogger(__name__)


@tool
def check_blend_orgid(loan_id: str) -> dict:
    """Check ORGID for Blend integration (G19 - LOW).
    
    Per GAPS.md G19 and SOP Video Notes Lines 226-227:
    - Read ORGID field
    - Verify value is set correctly
    
    Does NOT update - logs that it should be verified manually.
    Field: ORGID
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with ORGID check results
    """
    logger.info(f"[G19] Checking Blend ORGID for loan {loan_id[:8]}...")
    logger.info("[G19] Blend ORGID check - requires manual verification by LO")
    
    try:
        # Read ORGID field
        orgid = read_field(loan_id, "ORGID")
        
        result = {
            "gap_id": "G19",
            "gap_name": "Blend ORGID Check",
            "status": "read_only_check",
            "orgid": orgid,
            "message": "ORGID read successfully - manual verification recommended",
            "warnings": [
                "This is a read-only check - ORGID not updated automatically",
                "LO should verify ORGID value is correct for Blend integration"
            ],
        }
        
        if not orgid:
            result["warnings"].append("ORGID field is blank - may need to be set")
            logger.warning("[G19] ORGID field is blank")
        else:
            logger.info(f"[G19] ORGID value: {orgid}")
        
        return result
        
    except Exception as e:
        logger.error(f"[G19] Error checking ORGID: {e}")
        return {
            "gap_id": "G19",
            "gap_name": "Blend ORGID Check",
            "status": "error",
            "error": str(e),
        }


# Export tools
blend_tools = [
    check_blend_orgid,
]

