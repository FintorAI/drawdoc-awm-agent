"""MI calculation tools for disclosure preparation agent.

These tools allow the agent to calculate and populate MI fields.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from packages.shared import (
    get_encompass_client,
    read_fields,
    write_fields,
    get_loan_type,
    get_loan_summary,
    calculate_mi,
    calculate_conventional_mi,
    MICertData,
    LoanType,
    FieldIds,
)

logger = logging.getLogger(__name__)


@tool
def calculate_loan_mi(loan_id: str) -> dict:
    """Calculate Mortgage Insurance for a loan.
    
    This tool reads loan data from Encompass, calculates MI based on loan type,
    and returns the results. Use this before populating CD MI fields.
    
    MVP: Only Conventional loans are fully supported.
    FHA/VA/USDA return estimates (Phase 2).
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with MI calculation results:
        - requires_mi: Whether MI is required
        - loan_type: Loan type used for calculation
        - ltv: LTV percentage
        - upfront_amount: Upfront MI amount (if applicable)
        - monthly_amount: Monthly MI amount (if applicable)
        - annual_rate: Annual MI rate
        - cancel_at_ltv: LTV at which MI cancels (Conventional only)
        - source: "mi_cert" or "calculated"
        
    Example:
        result = calculate_loan_mi(loan_id)
        if result["requires_mi"]:
            print(f"Monthly MI: ${result['monthly_amount']}")
    """
    logger.info(f"[MI_TOOL] Calculating MI for loan {loan_id[:8]}...")
    
    try:
        # Get loan summary
        summary = get_loan_summary(loan_id)
        
        loan_type = summary.get("loan_type", "Unknown")
        loan_amount = summary.get("loan_amount")
        appraised_value = summary.get("appraised_value")
        ltv = summary.get("ltv")
        
        logger.info(f"[MI_TOOL] Loan type: {loan_type}, Amount: ${loan_amount:,.0f if loan_amount else 0}, LTV: {ltv}%")
        
        # Check if loan type is MVP supported
        if not LoanType.is_mvp_supported(loan_type):
            logger.warning(f"[MI_TOOL] Non-MVP loan type: {loan_type}")
            return {
                "success": False,
                "requires_mi": False,
                "loan_type": loan_type,
                "error": f"Non-MVP loan type: {loan_type}. Only Conventional is fully supported.",
                "is_mvp_supported": False,
            }
        
        # Validate required fields
        if loan_amount is None or loan_amount <= 0:
            return {
                "success": False,
                "error": "Loan amount is missing or invalid",
                "requires_mi": False,
            }
        
        if appraised_value is None or appraised_value <= 0:
            return {
                "success": False,
                "error": "Appraised value is missing or invalid",
                "requires_mi": False,
            }
        
        # Calculate MI
        result = calculate_mi(
            loan_type=loan_type,
            loan_amount=loan_amount,
            appraised_value=appraised_value,
            ltv=ltv,
        )
        
        logger.info(f"[MI_TOOL] MI calculation complete: requires_mi={result.requires_mi}")
        
        return {
            "success": True,
            "loan_id": loan_id,
            "is_mvp_supported": True,
            **result.to_dict(),
        }
        
    except Exception as e:
        logger.error(f"[MI_TOOL] Error calculating MI: {e}")
        return {
            "success": False,
            "error": str(e),
            "requires_mi": False,
        }


@tool
def populate_mi_fields(
    loan_id: str,
    monthly_amount: float,
    upfront_amount: Optional[float] = None,
    cancel_at_ltv: Optional[float] = None,
    dry_run: bool = True
) -> dict:
    """Populate MI fields in Encompass with calculated values.
    
    Use this after calculate_loan_mi to write MI values to Encompass fields.
    
    Args:
        loan_id: Encompass loan GUID
        monthly_amount: Monthly MI amount to write
        upfront_amount: Upfront MI amount (optional)
        cancel_at_ltv: LTV at which MI cancels (optional)
        dry_run: If True, simulate write only (default: True)
        
    Returns:
        Dictionary with write status:
        - success: Whether all writes succeeded
        - fields_written: List of field IDs written
        - dry_run: Whether this was a dry run
    """
    logger.info(f"[MI_TOOL] {'[DRY RUN] ' if dry_run else ''}Populating MI fields for loan {loan_id[:8]}...")
    
    try:
        updates = {}
        
        if monthly_amount is not None:
            updates[FieldIds.MI_MONTHLY_AMOUNT] = round(monthly_amount, 2)
        
        if upfront_amount is not None:
            updates[FieldIds.MI_UPFRONT_AMOUNT] = round(upfront_amount, 2)
        
        if cancel_at_ltv is not None:
            updates[FieldIds.MI_CANCEL_AT_LTV] = cancel_at_ltv
        
        if not updates:
            return {
                "success": True,
                "fields_written": [],
                "message": "No MI values to write",
                "dry_run": dry_run,
            }
        
        success = write_fields(loan_id, updates, dry_run=dry_run)
        
        return {
            "success": success,
            "fields_written": list(updates.keys()),
            "values": updates,
            "dry_run": dry_run,
            "message": f"{'Would write' if dry_run else 'Wrote'} {len(updates)} MI fields",
        }
        
    except Exception as e:
        logger.error(f"[MI_TOOL] Error populating MI fields: {e}")
        return {
            "success": False,
            "error": str(e),
            "fields_written": [],
        }


@tool
def check_mi_required(loan_id: str) -> dict:
    """Check if MI is required for a loan based on LTV.
    
    Quick check without full calculation - useful for early validation.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - requires_mi: Whether MI is likely required (LTV > 80%)
        - ltv: Current LTV
        - loan_type: Loan type
    """
    logger.info(f"[MI_TOOL] Checking if MI required for loan {loan_id[:8]}...")
    
    try:
        summary = get_loan_summary(loan_id)
        
        loan_type = summary.get("loan_type", "Unknown")
        ltv = summary.get("ltv")
        
        # Government loans always have MI/funding fee
        if loan_type in ["FHA", "VA", "USDA"]:
            return {
                "success": True,
                "requires_mi": True,
                "reason": f"{loan_type} loans always have MI/funding fee",
                "ltv": ltv,
                "loan_type": loan_type,
            }
        
        # Conventional requires MI if LTV > 80%
        if ltv is not None and ltv > 80:
            return {
                "success": True,
                "requires_mi": True,
                "reason": f"LTV ({ltv:.1f}%) exceeds 80%",
                "ltv": ltv,
                "loan_type": loan_type,
            }
        
        return {
            "success": True,
            "requires_mi": False,
            "reason": f"LTV ({ltv:.1f}% if ltv else 'N/A') does not exceed 80%",
            "ltv": ltv,
            "loan_type": loan_type,
        }
        
    except Exception as e:
        logger.error(f"[MI_TOOL] Error checking MI requirement: {e}")
        return {
            "success": False,
            "error": str(e),
            "requires_mi": False,
        }

