"""Template application tools for preparation agent.

Implements G7: Affiliate Business Arrangement template application.
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
def apply_aba_template(loan_id: str, dry_run: bool = False) -> dict:
    """Apply Affiliate Business Arrangement template (G7 - MEDIUM).
    
    Per GAPS.md G7 and SOP Video Notes Lines 85-86:
    - Check if ABA form is blank
    - Apply "AWM Affiliate" template
    - Mark Settlement checkbox
    - Mark Purchase/Sale/Refinance boxes
    
    All field IDs UNKNOWN - logs warning for manual application.
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, simulate operation without making changes
        
    Returns:
        Dictionary with template application results
    """
    logger.info(f"[G7] Applying ABA template for loan {loan_id[:8]}...")
    logger.warning("[G7] ABA template field IDs UNKNOWN - requires manual application in Encompass")
    
    if dry_run:
        logger.info("[G7] DRY RUN - Would apply AWM Affiliate template")
        return {
            "gap_id": "G7",
            "gap_name": "Affiliate Business Arrangement Template",
            "status": "dry_run",
            "message": "Dry run - no changes made",
            "template": "AWM Affiliate",
            "checkboxes_to_mark": ["Settlement", "Purchase/Sale/Refinance"],
        }
    
    return {
        "gap_id": "G7",
        "gap_name": "Affiliate Business Arrangement Template",
        "status": "manual_application_required",
        "message": "Please manually apply AWM Affiliate template in Encompass",
        "instructions": [
            "1. Check if ABA form is blank",
            "2. Click 'Apply Template' > 'AWM Affiliate' > OK",
            "3. Mark Settlement checkbox",
            "4. Mark Purchase/Sale/Refinance boxes"
        ],
        "warnings": [
            "ABA form blank detection field ID UNKNOWN - manual verification required",
            "Template application method field ID UNKNOWN - manual verification required",
            "Settlement checkbox field ID UNKNOWN - manual verification required",
            "Purchase/Sale/Refinance checkbox field IDs UNKNOWN - manual verification required"
        ],
        "requires_manual_verification": True,
    }


# Export tools
template_tools = [
    apply_aba_template,
]

