"""
Fee Mapping and APR Flag Validation Tools for Phase 3 CD Validation.

Implements SOP Step 19:
- Validate APR impact flags for origination fees and discount points
- Verify fees are in correct CD sections
- Validate PAC vs POC designations

Per SOP Step 19 - 2015 Itemization requirements.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS (Confirmed from Encompass)
# =============================================================================

class FeeMappingFields:
    """Encompass field IDs for fee mapping and APR validation."""
    
    # Core fee fields
    ORIGINATION_FEE = "454"  # Line 801
    DISCOUNT_POINTS = "1061"  # Line 802
    LENDER_CREDIT = "4794"  # Non-Specific Lender Credit
    
    # APR Impact Flags (Confirmed from Encompass)
    LINE_801_APR_FLAG = "SYS.X17"  # APR flag for Line 801 (Origination Fee)
    LINE_802_APR_FLAG = "NEWHUD.X1177"  # APR flag for Line 802 (Discount Points)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


# =============================================================================
# APR FLAG VALIDATION
# =============================================================================

def validate_apr_flags(loan_id: str) -> Dict[str, Any]:
    """
    Validate that origination fees and discount points have APR impact flags.
    
    Per SOP Step 19:
    - All origination fees (Line 801) MUST have "Impacts APR" checked
    - All discount points (Line 802) MUST have "Impacts APR" checked
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results and PTF conditions
    """
    logger.info(f"[APR FLAGS] Starting validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "violations": [],
        "line_801_checked": False,
        "line_802_checked": False,
        "details": []
    }
    
    try:
        # Read fee amounts and APR flags
        logger.info("[APR FLAGS] Reading fee fields and APR flags...")
        fields = read_fields(loan_id, [
            FeeMappingFields.ORIGINATION_FEE,
            FeeMappingFields.DISCOUNT_POINTS,
            FeeMappingFields.LINE_801_APR_FLAG,
            FeeMappingFields.LINE_802_APR_FLAG,
        ])
        
        if not fields:
            logger.warning("[APR FLAGS] No fields returned from Encompass")
            result["status"] = "error"
            result["details"].append("Unable to read fee fields from Encompass")
            return result
        
        # Extract values
        origination_fee = safe_float(fields.get(FeeMappingFields.ORIGINATION_FEE))
        discount_points = safe_float(fields.get(FeeMappingFields.DISCOUNT_POINTS))
        line_801_apr_flag = fields.get(FeeMappingFields.LINE_801_APR_FLAG)
        line_802_apr_flag = fields.get(FeeMappingFields.LINE_802_APR_FLAG)
        
        logger.info(f"[APR FLAGS] Origination Fee: {format_currency(origination_fee)}")
        logger.info(f"[APR FLAGS] Discount Points: {format_currency(discount_points)}")
        logger.info(f"[APR FLAGS] Line 801 APR Flag: {line_801_apr_flag}")
        logger.info(f"[APR FLAGS] Line 802 APR Flag: {line_802_apr_flag}")
        
        # Check if APR flags are checked
        # APR flags are typically "X" or "Y" or "1" when checked, empty/null when unchecked
        line_801_checked = bool(line_801_apr_flag and str(line_801_apr_flag).strip().upper() in ["X", "Y", "1", "TRUE", "YES"])
        line_802_checked = bool(line_802_apr_flag and str(line_802_apr_flag).strip().upper() in ["X", "Y", "1", "TRUE", "YES"])
        
        result["line_801_checked"] = line_801_checked
        result["line_802_checked"] = line_802_checked
        
        # =====================================================================
        # LINE 801 VALIDATION (Origination Fee)
        # =====================================================================
        if origination_fee > 0.01:  # Only check if fee exists
            if not line_801_checked:
                result["violations"].append({
                    "type": "PTF",
                    "severity": "MEDIUM",
                    "category": "APR Flag Missing",
                    "field_id": FeeMappingFields.LINE_801_APR_FLAG,
                    "field_name": "Line 801 APR Impact Flag",
                    "message": f"Origination fee (Line 801) of {format_currency(origination_fee)} is missing 'Impacts APR' flag",
                    "details": {
                        "origination_fee": format_currency(origination_fee),
                        "apr_flag_value": str(line_801_apr_flag) if line_801_apr_flag else "Empty/Unchecked",
                        "required": "APR flag must be checked for all origination fees"
                    },
                    "action_required": "Check 'Impacts APR' checkbox for Line 801 (Origination Fee) in 2015 Itemization form",
                    "fields_affected": [FeeMappingFields.ORIGINATION_FEE, FeeMappingFields.LINE_801_APR_FLAG],
                    "sop_reference": "Step 19 - 2015 Itemization",
                    "compliance_issue": "Origination fees must impact APR calculation per TRID requirements"
                })
                logger.warning(f"[APR FLAGS] ⚠️  Line 801 missing APR flag")
            else:
                logger.info("[APR FLAGS] ✅ Line 801 APR flag checked")
        
        # =====================================================================
        # LINE 802 VALIDATION (Discount Points)
        # =====================================================================
        if discount_points > 0.01:  # Only check if points exist
            if not line_802_checked:
                result["violations"].append({
                    "type": "PTF",
                    "severity": "MEDIUM",
                    "category": "APR Flag Missing",
                    "field_id": FeeMappingFields.LINE_802_APR_FLAG,
                    "field_name": "Line 802 APR Impact Flag",
                    "message": f"Discount points (Line 802) of {format_currency(discount_points)} is missing 'Impacts APR' flag",
                    "details": {
                        "discount_points": format_currency(discount_points),
                        "apr_flag_value": str(line_802_apr_flag) if line_802_apr_flag else "Empty/Unchecked",
                        "required": "APR flag must be checked for all discount points"
                    },
                    "action_required": "Check 'Impacts APR' checkbox for Line 802 (Discount Points) in 2015 Itemization form",
                    "fields_affected": [FeeMappingFields.DISCOUNT_POINTS, FeeMappingFields.LINE_802_APR_FLAG],
                    "sop_reference": "Step 19 - 2015 Itemization",
                    "compliance_issue": "Discount points must impact APR calculation per TRID requirements"
                })
                logger.warning(f"[APR FLAGS] ⚠️  Line 802 missing APR flag")
            else:
                logger.info("[APR FLAGS] ✅ Line 802 APR flag checked")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        if len(result["violations"]) > 0:
            result["status"] = "violations_found"
            logger.warning(f"[APR FLAGS] Found {len(result['violations'])} APR flag violations")
        else:
            result["status"] = "compliant"
            logger.info("[APR FLAGS] ✅ All APR flags correct")
        
        # Add summary details
        result["details"].append(f"Line 801 APR Flag: {'Checked' if line_801_checked else 'Missing'}")
        result["details"].append(f"Line 802 APR Flag: {'Checked' if line_802_checked else 'Missing'}")
        
        return result
        
    except Exception as e:
        logger.error(f"[APR FLAGS] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_apr_flags",
]



