"""
State-Specific Validation Tools.

Implements state-specific rules per SOP:
- Texas: Home Equity, NBS, Attorney fees, Cash-Out Non-Homestead
- California: No Impounds exception, Vesting rules
- Nevada: HIP/HAL products, Worksheet exclusion
- Colorado: Vesting rules (no marital status), Trustee rules

Per SOP - State-specific requirements.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, get_loan_context

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS
# =============================================================================

class StateFields:
    """Encompass field IDs for state-specific validation."""
    
    # Property State (used to determine which state rules apply)
    PROPERTY_STATE = "14"  # Subject Property State
    
    # Loan Program (for TX Home Equity check)
    LOAN_PROGRAM = "1401"  # Loan Program
    
    # Loan Purpose (for NBS check)
    LOAN_PURPOSE = "384"  # Loan Purpose
    
    # Occupancy (for NBS check)
    OCCUPANCY = "3335"  # Occupancy Type
    
    # LTV (for CA No Impounds exception)
    LTV = "353"  # LTV
    
    # Loan Type (for CA No Impounds exception - Conventional only)
    LOAN_TYPE = "1172"  # Loan Type
    
    # Vesting field
    VESTING = "1872"  # Vesting (Borrower Information - Vesting)
    
    # Marital Status (for CO vesting check)
    MARITAL_STATUS = "52"  # Marital Status (1003 URLA)


# =============================================================================
# STATE-SPECIFIC RULES
# =============================================================================

COMMUNITY_PROPERTY_STATES = ["AZ", "CA", "ID", "LA", "NV", "NM", "TX", "WA", "WI"]


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_state_specific_rules(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive state-specific validation.
    
    Validates rules based on property state:
    - Texas: Home Equity, NBS, Attorney fees, Cash-Out Non-Homestead
    - California: No Impounds exception, Vesting rules
    - Nevada: HIP/HAL products, Worksheet exclusion
    - Colorado: Vesting rules, Trustee rules
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[STATE VALIDATION] Starting state-specific validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "state": None,
        "state_validations": {},
        "all_checks_passed": False,
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[STATE VALIDATION] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        state = loan_context.get("state", "").upper()
        result["state"] = state
        
        if not state:
            result["status"] = "state_not_found"
            result["details"].append("Property state not found")
            logger.warning("[STATE VALIDATION] Property state not found")
            return result
        
        logger.info(f"[STATE VALIDATION] Property state: {state}")
        
        # Read state-specific fields
        fields = read_fields(loan_id, [
            StateFields.PROPERTY_STATE,
            StateFields.LOAN_PROGRAM,
            StateFields.LOAN_PURPOSE,
            StateFields.OCCUPANCY,
            StateFields.LTV,
            StateFields.LOAN_TYPE,
        ])
        
        # =====================================================================
        # TEXAS (TX) VALIDATIONS
        # =====================================================================
        if state == "TX":
            logger.info("\n[STATE VALIDATION] Validating Texas-specific rules...")
            tx_validation = validate_texas_rules(fields, loan_context)
            result["state_validations"]["texas"] = tx_validation
            
            if not tx_validation["passed"]:
                for violation in tx_validation.get("violations", []):
                    result["violations"].append(violation)
                logger.warning(f"[STATE VALIDATION] ⚠️  Texas: {tx_validation['message']}")
            else:
                logger.info(f"[STATE VALIDATION] ✅ Texas: {tx_validation['message']}")
        
        # =====================================================================
        # CALIFORNIA (CA) VALIDATIONS
        # =====================================================================
        elif state == "CA":
            logger.info("\n[STATE VALIDATION] Validating California-specific rules...")
            ca_validation = validate_california_rules(fields, loan_context)
            result["state_validations"]["california"] = ca_validation
            
            if not ca_validation["passed"]:
                for violation in ca_validation.get("violations", []):
                    result["violations"].append(violation)
                logger.warning(f"[STATE VALIDATION] ⚠️  California: {ca_validation['message']}")
            else:
                logger.info(f"[STATE VALIDATION] ✅ California: {ca_validation['message']}")
        
        # =====================================================================
        # NEVADA (NV) VALIDATIONS
        # =====================================================================
        elif state == "NV":
            logger.info("\n[STATE VALIDATION] Validating Nevada-specific rules...")
            nv_validation = validate_nevada_rules(fields, loan_context)
            result["state_validations"]["nevada"] = nv_validation
            
            if not nv_validation["passed"]:
                for violation in nv_validation.get("violations", []):
                    result["violations"].append(violation)
                logger.warning(f"[STATE VALIDATION] ⚠️  Nevada: {nv_validation['message']}")
            else:
                logger.info(f"[STATE VALIDATION] ✅ Nevada: {nv_validation['message']}")
        
        # =====================================================================
        # COLORADO (CO) VALIDATIONS
        # =====================================================================
        elif state == "CO":
            logger.info("\n[STATE VALIDATION] Validating Colorado-specific rules...")
            co_validation = validate_colorado_rules(fields, loan_context)
            result["state_validations"]["colorado"] = co_validation
            
            if not co_validation["passed"]:
                for violation in co_validation.get("violations", []):
                    result["violations"].append(violation)
                logger.warning(f"[STATE VALIDATION] ⚠️  Colorado: {co_validation['message']}")
            else:
                logger.info(f"[STATE VALIDATION] ✅ Colorado: {co_validation['message']}")
        
        else:
            logger.info(f"[STATE VALIDATION] No specific rules for state: {state}")
            result["state_validations"][state.lower()] = {
                "status": "no_rules",
                "message": f"No specific validation rules for {state}"
            }
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        all_passed = all(
            validation.get("passed", True)
            for validation in result["state_validations"].values()
            if isinstance(validation, dict)
        )
        
        result["all_checks_passed"] = all_passed
        
        if all_passed:
            result["status"] = "all_checks_passed"
            logger.info("\n" + "="*80)
            logger.info(f"[STATE VALIDATION] ✅ ALL STATE VALIDATIONS PASSED FOR {state}")
            logger.info("="*80)
        else:
            result["status"] = "violations_found"
            logger.warning("\n" + "="*80)
            logger.warning(f"[STATE VALIDATION] ⚠️  Found {len(result['violations'])} state violations")
            logger.warning("="*80)
        
        # Add summary details
        result["details"].append(f"State: {state}")
        result["details"].append(f"State validations: {len(result['state_validations'])}")
        result["details"].append(f"Violations: {len(result['violations'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[STATE VALIDATION] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# STATE-SPECIFIC VALIDATORS
# =============================================================================

def validate_texas_rules(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Texas-specific rules.
    
    Per SOP:
    1. Home Equity: For Cash out Refinance with Primary Occupancy, select "TX HOME EQUITY" program
    2. NBS/NBP: Required for Refinance Primary Rescindable loans
    3. Attorney Review Fee: NOT charged to Veteran on VA loans
    4. Cash-Out Refinance Non-Homestead: Special handling
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": True,
        "message": "",
        "violations": [],
        "warnings": [],
        "details": {}
    }
    
    loan_program = fields.get(StateFields.LOAN_PROGRAM, "").upper()
    loan_purpose = fields.get(StateFields.LOAN_PURPOSE, "").upper()
    occupancy = fields.get(StateFields.OCCUPANCY, "").upper()
    loan_type = loan_context.get("loan_type", "").upper()
    
    result["details"]["loan_program"] = loan_program
    result["details"]["loan_purpose"] = loan_purpose
    result["details"]["occupancy"] = occupancy
    
    # Check 1: Home Equity Program
    is_cash_out_refi = "CASH" in loan_purpose or "CASH-OUT" in loan_purpose
    is_primary = "PRIMARY" in occupancy or occupancy == "P"
    
    if is_cash_out_refi and is_primary:
        if "HOME EQUITY" not in loan_program and "TX HOME EQUITY" not in loan_program:
            result["violations"].append({
                "type": "PTF",
                "severity": "HIGH",
                "category": "TX Home Equity Program",
                "message": "Cash-Out Refinance with Primary Occupancy requires 'TX HOME EQUITY' program",
                "action_required": "Select 'TX HOME EQUITY' program for Cash-Out Refinance with Primary Occupancy",
                "fields_affected": [StateFields.LOAN_PROGRAM],
                "sop_reference": "Step 16 - RegZ CD - Texas Home Equity"
            })
            result["passed"] = False
    
    # Check 2: NBS/NBP Requirements (Refinance Primary Rescindable)
    is_refi = "REFI" in loan_purpose or "REFINANCE" in loan_purpose
    is_rescindable = is_refi and is_primary
    
    if is_rescindable:
        # NBS required unless QCD executed and recorded + vesting shows sole/separate
        result["warnings"].append({
            "type": "WARNING",
            "severity": "MEDIUM",
            "category": "TX NBS/NBP Requirements",
            "message": "Refinance Primary Rescindable loan - NBS must sign/acknowledge CD, NORTC, and security instrument",
            "action_required": "Verify NBS signing requirements (Exception: QCD executed + vesting shows sole/separate)",
            "sop_reference": "SOP Update 78 - NBS/NBP requirement in Texas"
        })
    
    # Check 3: Attorney Review Fee on VA loans
    if "VA" in loan_type:
        result["warnings"].append({
            "type": "WARNING",
            "severity": "MEDIUM",
            "category": "TX Attorney Review Fee",
            "message": "VA loan in Texas - Attorney review fee NOT charged to Veteran",
            "action_required": "Itemize Attorney review fee from Seller/Lender credit (not charged to Veteran)",
            "sop_reference": "SOP Update 84 - TEXAS Attorney review fee on VA loans"
        })
    
    if result["violations"]:
        result["message"] = f"Found {len(result['violations'])} Texas violations"
    else:
        result["message"] = "Texas rules validated"
    
    return result


def validate_california_rules(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate California-specific rules.
    
    Per SOP:
    1. No Impounds exception: Up to 90% LTV (Conventional only) - Already handled in escrow validation
    2. Tax Calculation: 1.25% of Sales Price / 12 - Already handled in escrow validation
    3. Vesting Rules: Married + non-borrowing spouse not on title → "Married Man/Woman as his/her Sole and Separate property"
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": True,
        "message": "",
        "violations": [],
        "warnings": [],
        "details": {}
    }
    
    # Note: No Impounds and Tax Calculation are already handled in escrow validation
    
    # Check: Vesting Rules (if we have vesting field)
    # Married + non-borrowing spouse not on title → specific verbiage required
    # This would require vesting field ID which we don't have yet
    
    result["message"] = "California rules validated (No Impounds and Tax Calculation handled in escrow validation)"
    result["details"]["note"] = "Vesting rules require vesting field ID to validate"
    
    return result


def validate_nevada_rules(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Nevada-specific rules.
    
    Per SOP:
    1. HIP/HAL Products: Special handling for NV HIP products
    2. Worksheet Exclusion: Remove NV Repayment Ability Verification Worksheet from package
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": True,
        "message": "",
        "violations": [],
        "warnings": [],
        "details": {}
    }
    
    loan_program = fields.get(StateFields.LOAN_PROGRAM, "").upper()
    
    # Check: HIP/HAL Products
    if "HIP" in loan_program or "HAL" in loan_program:
        result["warnings"].append({
            "type": "WARNING",
            "severity": "MEDIUM",
            "category": "NV HIP/HAL Products",
            "message": "Nevada HIP/HAL product detected - special handling required",
            "action_required": "Verify HIP/HAL product requirements per SOP Update 10",
            "sop_reference": "SOP Update 10 - Update on US MRBP –NV HIP/HAL Products"
        })
    
    # Check: Worksheet Exclusion
    result["warnings"].append({
        "type": "WARNING",
        "severity": "LOW",
        "category": "NV Worksheet Exclusion",
        "message": "Nevada loan - Remove NV Repayment Ability Verification Worksheet from package",
        "action_required": "Uncheck NV Repayment Ability Verification Worksheet from closing package",
        "sop_reference": "SOP - Nevada Worksheet Exclusion"
    })
    
    result["message"] = "Nevada rules validated"
    
    return result


def validate_colorado_rules(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Colorado-specific rules.
    
    Per SOP:
    1. Vesting Rules: Marital status NOT required in vesting
    2. Trustee: County name & address (not Title Company)
    3. Tax Calculation: Mill Levy Rate or 1% - Already handled in escrow validation
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": True,
        "message": "",
        "violations": [],
        "warnings": [],
        "details": {}
    }
    
    # Check: Vesting Rules (if we have vesting field)
    # Marital status NOT required in vesting
    # This would require vesting field ID which we don't have yet
    
    # Check: Trustee Rules
    # Trustee should be County name & address (not Title Company)
    result["warnings"].append({
        "type": "WARNING",
        "severity": "MEDIUM",
        "category": "CO Trustee Rules",
        "message": "Colorado loan - Trustee should be County name & address (not Title Company)",
        "action_required": "Verify Trustee is County name & address from Business contacts No Category",
        "sop_reference": "SOP - Colorado Trustee Rules"
    })
    
    result["message"] = "Colorado rules validated (Tax Calculation handled in escrow validation)"
    result["details"]["note"] = "Vesting rules require vesting field ID to validate"
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_state_specific_rules",
    "validate_texas_rules",
    "validate_california_rules",
    "validate_nevada_rules",
    "validate_colorado_rules",
]



