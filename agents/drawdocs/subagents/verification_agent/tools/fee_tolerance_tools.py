"""
Fee Tolerance Validation Tools for Phase 3 CD Validation.

Implements SOP Steps 19-20:
- Section A: 0% tolerance (cannot increase at all)
- Section B: 10% aggregate tolerance
- Section C: No tolerance (borrower shopped)
- Auto-calculate required cure amounts
- Generate PTF conditions for violations

Per RESPA/TRID compliance requirements.
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
# FIELD MAPPINGS (All confirmed from master_field_data.csv)
# =============================================================================

class FeeToleranceFields:
    """Encompass field IDs for fee tolerance validation."""
    
    # Core fee fields
    ORIGINATION_FEE = "454"  # Line 801
    DISCOUNT_POINTS = "1061"  # Line 802
    LENDER_CREDIT = "4794"  # Non-Specific Lender Credit
    
    # CD Page 2 - Section Subtotals (Current CD)
    SECTION_A_SUBTOTAL = "CD2.XSTA"  # Origination Charges
    SECTION_B_SUBTOTAL = "CD2.XSTB"  # Services Borrower Did Not Shop For
    SECTION_C_SUBTOTAL = "CD2.XSTC"  # Services Borrower Did Shop For
    SECTION_E_SUBTOTAL = "CD2.XSTE"  # Taxes and Government Fees
    SECTION_F_SUBTOTAL = "CD2.XSTF"  # Prepaids
    SECTION_G_SUBTOTAL = "CD2.XSTG"  # Initial Escrow Payment
    SECTION_H_SUBTOTAL = "CD2.XSTH"  # Other
    SECTION_J_TOTAL = "CD2.XSTJ"  # Total Closing Costs (Borrower Paid)
    
    # CD Page 2 - Last Disclosed Amounts (From previous LE or CD)
    LAST_DISCLOSED_LOAN_COSTS = "CD2.XLDLC"  # Last disclosed loan costs
    LAST_DISCLOSED_OTHER_COSTS = "CD2.XLDOC"  # Last disclosed other costs
    LAST_DISCLOSED_LENDER_CREDITS = "CD2.XLDLCR"  # Last disclosed lender credits
    
    # LE Page 2 - Section Subtotals (For baseline comparison)
    LE_SECTION_B_SUBTOTAL = "LE2.XSTB"  # LE Section B subtotal (Services Not Shopped)
    SECTION_D_TOTAL = "CD2.XSTD"  # Section D Total Loan Costs
    
    # CD Page 2 - Borrower/Seller Paid breakdown
    BORROWER_PAID_AT_CLOSING = "CD2.XLCAC"
    BORROWER_PAID_BEFORE_CLOSING = "CD2.XLCBC"
    
    # CD Page 1 - Tolerance Cure tracking
    TOLERANCE_CURE = "CD1.X57"
    CHANGED_CIRCUMSTANCE_CHECKBOX = "CD1.X61"
    CHANGED_CIRCUMSTANCE_DATE = "CD1.X62"


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
# MAIN VALIDATION FUNCTIONS
# =============================================================================

def validate_fee_tolerance(loan_id: str, loan_type: str = "Conventional") -> Dict[str, Any]:
    """
    Validate fee tolerance rules per RESPA/TRID.
    
    Per SOP Step 20 (Fee Variance):
    - Section A (0% tolerance): Origination charges CANNOT increase at all
    - Section B (10% tolerance): Services not shopped can increase up to 10% aggregate
    - Section C (no tolerance): Services shopped by borrower can increase freely
    
    Args:
        loan_id: Encompass loan GUID
        loan_type: Type of loan (for context in messages)
        
    Returns:
        Dictionary with validation results and PTF conditions
    """
    logger.info(f"[FEE TOLERANCE] Starting validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "loan_type": loan_type,
        "violations": [],
        "section_a_analysis": {},
        "section_b_analysis": {},
        "total_required_cure": 0.0,
        "details": []
    }
    
    try:
        # Read all fee tolerance fields
        logger.info("[FEE TOLERANCE] Reading CD subtotals and last disclosed amounts...")
        fields = read_fields(loan_id, [
            # Current CD subtotals
            FeeToleranceFields.SECTION_A_SUBTOTAL,
            FeeToleranceFields.SECTION_B_SUBTOTAL,
            FeeToleranceFields.SECTION_C_SUBTOTAL,
            FeeToleranceFields.SECTION_D_TOTAL,
            FeeToleranceFields.SECTION_E_SUBTOTAL,
            FeeToleranceFields.SECTION_F_SUBTOTAL,
            FeeToleranceFields.SECTION_G_SUBTOTAL,
            FeeToleranceFields.SECTION_H_SUBTOTAL,
            FeeToleranceFields.SECTION_J_TOTAL,
            # Last disclosed amounts
            FeeToleranceFields.LAST_DISCLOSED_LOAN_COSTS,
            FeeToleranceFields.LAST_DISCLOSED_OTHER_COSTS,
            FeeToleranceFields.LAST_DISCLOSED_LENDER_CREDITS,
            # LE baseline for Section B
            FeeToleranceFields.LE_SECTION_B_SUBTOTAL,
            # Individual fees (for detail)
            FeeToleranceFields.ORIGINATION_FEE,
            FeeToleranceFields.DISCOUNT_POINTS,
            FeeToleranceFields.LENDER_CREDIT,
            # Cure tracking
            FeeToleranceFields.TOLERANCE_CURE,
            FeeToleranceFields.CHANGED_CIRCUMSTANCE_CHECKBOX,
        ])
        
        if not fields:
            logger.warning("[FEE TOLERANCE] No fields returned from Encompass")
            result["status"] = "error"
            result["details"].append("Unable to read fee fields from Encompass")
            return result
        
        # Extract current CD values
        current_section_a = safe_float(fields.get(FeeToleranceFields.SECTION_A_SUBTOTAL))
        current_section_b = safe_float(fields.get(FeeToleranceFields.SECTION_B_SUBTOTAL))
        current_section_c = safe_float(fields.get(FeeToleranceFields.SECTION_C_SUBTOTAL))
        
        # Extract last disclosed values
        last_disclosed_loan_costs = safe_float(fields.get(FeeToleranceFields.LAST_DISCLOSED_LOAN_COSTS))
        
        # Extract individual fees for detail
        origination_fee = safe_float(fields.get(FeeToleranceFields.ORIGINATION_FEE))
        discount_points = safe_float(fields.get(FeeToleranceFields.DISCOUNT_POINTS))
        lender_credit = safe_float(fields.get(FeeToleranceFields.LENDER_CREDIT))
        
        logger.info(f"[FEE TOLERANCE] Current Section A: {format_currency(current_section_a)}")
        logger.info(f"[FEE TOLERANCE] Current Section B: {format_currency(current_section_b)}")
        logger.info(f"[FEE TOLERANCE] Last Disclosed Loan Costs: {format_currency(last_disclosed_loan_costs)}")
        
        # =====================================================================
        # SECTION A VALIDATION (0% Tolerance)
        # =====================================================================
        logger.info("\n[FEE TOLERANCE] Validating Section A (0% tolerance)...")
        
        section_a_result = validate_section_a(
            current_section_a=current_section_a,
            last_disclosed_loan_costs=last_disclosed_loan_costs,
            origination_fee=origination_fee,
            discount_points=discount_points,
            lender_credit=lender_credit
        )
        
        result["section_a_analysis"] = section_a_result
        
        if section_a_result["violation_found"]:
            result["violations"].extend(section_a_result["violations"])
            result["total_required_cure"] += section_a_result["required_cure"]
            logger.warning(f"[FEE TOLERANCE] ⚠️  Section A violation: {format_currency(section_a_result['required_cure'])} cure required")
        else:
            logger.info("[FEE TOLERANCE] ✅ Section A compliant")
        
        # =====================================================================
        # SECTION B VALIDATION (10% Aggregate Tolerance)
        # =====================================================================
        logger.info("\n[FEE TOLERANCE] Validating Section B (10% aggregate tolerance)...")
        
        # Get last disclosed Section B (use LE Section B as baseline if last disclosed not available)
        last_disclosed_section_b = safe_float(fields.get(FeeToleranceFields.LE_SECTION_B_SUBTOTAL))
        # If we have last disclosed loan costs, try to calculate Section B from it
        # (Section B = Last Disclosed Loan Costs - Section A from LE)
        if last_disclosed_loan_costs > 0 and last_disclosed_section_b == 0:
            # Estimate: Section B ≈ Last Disclosed Loan Costs - Section A (rough estimate)
            # This is a fallback - ideally we'd have the actual last disclosed Section B
            logger.info("[FEE TOLERANCE] Using LE Section B as baseline for Section B tolerance")
        
        section_b_result = validate_section_b(
            current_section_b=current_section_b,
            last_disclosed_section_b=last_disclosed_section_b if last_disclosed_section_b > 0 else 0.0
        )
        
        result["section_b_analysis"] = section_b_result
        
        if section_b_result["violation_found"]:
            result["violations"].extend(section_b_result["violations"])
            result["total_required_cure"] += section_b_result["required_cure"]
            logger.warning(f"[FEE TOLERANCE] ⚠️  Section B violation: {format_currency(section_b_result['required_cure'])} cure required")
        else:
            logger.info("[FEE TOLERANCE] ✅ Section B compliant")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        if len(result["violations"]) > 0:
            result["status"] = "violations_found"
            logger.warning(f"[FEE TOLERANCE] Found {len(result['violations'])} tolerance violations")
            logger.warning(f"[FEE TOLERANCE] Total required cure: {format_currency(result['total_required_cure'])}")
        else:
            result["status"] = "compliant"
            logger.info("[FEE TOLERANCE] ✅ All fee tolerances compliant")
        
        # Add summary details
        result["details"].append(f"Section A (0% tolerance): {'VIOLATION' if section_a_result['violation_found'] else 'Compliant'}")
        result["details"].append(f"Section B (10% tolerance): {'VIOLATION' if section_b_result['violation_found'] else 'Compliant'}")
        result["details"].append(f"Total required cure: {format_currency(result['total_required_cure'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FEE TOLERANCE] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


def validate_section_a(
    current_section_a: float,
    last_disclosed_loan_costs: float,
    origination_fee: float,
    discount_points: float,
    lender_credit: float
) -> Dict[str, Any]:
    """
    Validate Section A (Origination Charges) - 0% tolerance.
    
    Per SOP Step 20:
    Section A fees (origination charges) CANNOT increase AT ALL.
    Any increase requires a tolerance cure.
    
    Args:
        current_section_a: Current Section A subtotal
        last_disclosed_loan_costs: Last disclosed loan costs (from LE or previous CD)
        origination_fee: Current origination fee (Line 801)
        discount_points: Current discount points (Line 802)
        lender_credit: Current lender credit
        
    Returns:
        Dictionary with Section A analysis and violations
    """
    result = {
        "current_total": current_section_a,
        "last_disclosed_total": last_disclosed_loan_costs,
        "increase_amount": 0.0,
        "tolerance_limit": 0.0,  # 0% tolerance
        "violation_found": False,
        "required_cure": 0.0,
        "violations": [],
        "fee_breakdown": {
            "origination_fee": origination_fee,
            "discount_points": discount_points,
            "lender_credit": lender_credit
        }
    }
    
    # Calculate increase
    increase = current_section_a - last_disclosed_loan_costs
    result["increase_amount"] = increase
    
    # Section A has 0% tolerance - ANY increase is a violation
    if increase > 0.01:  # Allow for $0.01 rounding tolerance
        result["violation_found"] = True
        result["required_cure"] = increase
        
        result["violations"].append({
            "type": "PTF",
            "severity": "HARD_STOP",
            "category": "Fee Tolerance Violation",
            "section": "Section A (Origination Charges)",
            "rule": "0% Tolerance - Cannot Increase",
            "message": f"Section A fees increased by {format_currency(increase)}. Section A has 0% tolerance and CANNOT increase at all.",
            "details": {
                "current_section_a": format_currency(current_section_a),
                "last_disclosed": format_currency(last_disclosed_loan_costs),
                "increase": format_currency(increase),
                "tolerance_limit": format_currency(0.0),
                "overage": format_currency(increase),
                "required_cure": format_currency(increase)
            },
            "action_required": f"Apply {format_currency(increase)} cure to Lender Credit (Field 4794)",
            "fields_affected": ["CD2.XSTA", "454", "1061", "4794"],
            "sop_reference": "Step 20 - Fee Variance (Zero Tolerance)",
            "compliance_issue": "RESPA/TRID Section A 0% Tolerance Violation"
        })
    
    return result


def validate_section_b(
    current_section_b: float,
    last_disclosed_section_b: float
) -> Dict[str, Any]:
    """
    Validate Section B (Services Borrower Did Not Shop For) - 10% aggregate tolerance.
    
    Per SOP Step 20:
    Section B fees can increase up to 10% in aggregate.
    Any increase beyond 10% requires a tolerance cure.
    
    Args:
        current_section_b: Current Section B subtotal
        last_disclosed_section_b: Last disclosed Section B amount
        
    Returns:
        Dictionary with Section B analysis and violations
    """
    result = {
        "current_total": current_section_b,
        "last_disclosed_total": last_disclosed_section_b,
        "increase_amount": 0.0,
        "tolerance_limit": 0.0,
        "tolerance_percent": 0.10,  # 10% tolerance
        "violation_found": False,
        "required_cure": 0.0,
        "violations": []
    }
    
    # Calculate tolerance limit (10% of last disclosed)
    tolerance_limit = last_disclosed_section_b * 0.10
    result["tolerance_limit"] = tolerance_limit
    
    # Calculate increase
    increase = current_section_b - last_disclosed_section_b
    result["increase_amount"] = increase
    
    # Check if increase exceeds 10% tolerance
    if increase > tolerance_limit + 0.01:  # Allow for $0.01 rounding tolerance
        result["violation_found"] = True
        overage = increase - tolerance_limit
        result["required_cure"] = overage
        
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Fee Tolerance Violation",
            "section": "Section B (Services Not Shopped)",
            "rule": "10% Aggregate Tolerance Exceeded",
            "message": f"Section B fees increased by {format_currency(increase)}, exceeding the 10% tolerance limit of {format_currency(tolerance_limit)}.",
            "details": {
                "current_section_b": format_currency(current_section_b),
                "last_disclosed": format_currency(last_disclosed_section_b),
                "increase": format_currency(increase),
                "tolerance_limit": format_currency(tolerance_limit),
                "overage": format_currency(overage),
                "required_cure": format_currency(overage)
            },
            "action_required": f"Apply {format_currency(overage)} cure to Lender Credit (Field 4794)",
            "fields_affected": ["CD2.XSTB", "4794"],
            "sop_reference": "Step 20 - Fee Variance (10% Tolerance)",
            "compliance_issue": "RESPA/TRID Section B 10% Aggregate Tolerance Violation"
        })
    
    return result


# =============================================================================
# CURE CALCULATION HELPERS
# =============================================================================

def calculate_total_required_cure(section_a_cure: float, section_b_cure: float) -> float:
    """Calculate total required cure amount."""
    return section_a_cure + section_b_cure


def generate_cure_application_instructions(total_cure: float) -> Dict[str, Any]:
    """
    Generate instructions for applying tolerance cures.
    
    Per SOP Step 20:
    - Cure is typically applied to Lender Credit (Field 4794)
    - Sometimes applied to Principal Reduction (rare)
    
    Args:
        total_cure: Total cure amount needed
        
    Returns:
        Dictionary with cure application instructions
    """
    return {
        "total_cure_required": format_currency(total_cure),
        "primary_method": {
            "field_id": "4794",
            "field_name": "Non-Specific Lender Credit",
            "action": f"Increase Lender Credit by {format_currency(total_cure)}",
            "location": "Encompass >> Forms >> 2015 Itemization >> Line 802"
        },
        "alternative_method": {
            "action": "Apply cure to Principal Reduction (POC)",
            "when_to_use": "Only when lender credit would make CD confusing or cause issues",
            "location": "Encompass >> Tools >> Fee Variance Worksheet"
        },
        "documentation_required": {
            "fee_variance_worksheet": "Document cure in Fee Variance Worksheet",
            "milestone_comments": f"Add comment: 'Tolerance cure of {format_currency(total_cure)} applied'",
            "resolved_by": "Your name",
            "date_applied": "Current date"
        }
    }


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_fee_tolerance",
    "validate_section_a",
    "validate_section_b",
    "calculate_total_required_cure",
    "generate_cure_application_instructions",
]

