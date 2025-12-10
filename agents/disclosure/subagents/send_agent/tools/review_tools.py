"""LO Review workflow tools for send agent.

Implements G21: LO to Review workflow.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

logger = logging.getLogger(__name__)


@tool
def set_lo_review_status(loan_id: str) -> dict:
    """Set disclosure status to 'LO to Review' (G21 - LOW).
    
    Per GAPS.md G21 and SOP Video Notes Lines 232-236:
    - Set loan status to "LO to Review"
    - Email should be sent to LO (manual process)
    
    Manual workflow - logs that email must be sent manually.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with review status update results
    """
    logger.info(f"[G21] Setting LO review status for loan {loan_id[:8]}...")
    logger.info("[G21] Manual workflow - email must be sent to LO separately")
    
    # This would require:
    # 1. Update loan status/milestone to "LO to Review"
    # 2. Trigger email notification to LO
    # Field IDs and workflow not fully defined
    
    return {
        "gap_id": "G21",
        "gap_name": "LO Review Workflow",
        "status": "manual_workflow",
        "message": "Loan ready for LO review - manual email notification required",
        "instructions": [
            "1. Update loan status to 'LO to Review'",
            "2. Send email to LO with disclosure package",
            "3. LO reviews and approves before sending to borrower"
        ],
        "warnings": [
            "Status update field ID not configured",
            "Email notification must be sent manually"
        ],
        "requires_manual_action": True,
    }


# Export tools
review_tools = [
    set_lo_review_status,
]

