"""
Closing Conditions Management Tools.

Implements SOP Step 8: Closing Conditions validation and management.

Per SOP:
- Title Report Expiration: 60th day from Effective Date
- CPL Expiration: 30th day from Effective Date
- Consummation Date: Closing/Signing date
- Copy PTF conditions from UW Conditions tab
- FHA 92900-A Page 3 condition (if missing)
- Property Tax installment conditions
- HOI renewal conditions

Note: This tool validates and generates conditions. Actual addition to Encompass
requires field IDs for Title Report Effective Date, CPL Effective Date, etc.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, get_loan_context, list_ptf_conditions

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS
# =============================================================================

class ClosingConditionFields:
    """Encompass field IDs for closing conditions."""
    
    # Basic Info
    PROPERTY_STATE = "14"  # Subject Property State
    PROPERTY_COUNTY = "15"  # Subject Property County
    LOAN_TYPE = "1172"  # Loan Type
    
    # Dates
    TITLE_REPORT_EFFECTIVE_DATE = None  # Title Report Effective Date - document-based only
    CPL_EFFECTIVE_DATE = None  # CPL Effective Date - document-based only
    CLOSING_DATE = "748"  # Closing Date (CD form)
    DISBURSEMENT_DATE = "2553"  # Disbursement Date
    FIRST_PAYMENT_DATE = "682"  # First Payment Date (1st Payment Date)
    NOTE_DATE = None  # Note Date - field not accessible in Encompass
    
    # HOI
    HOI_EXPIRATION_DATE = None  # HOI Expiration Date - not found in system
    HOI_ANNUAL_PREMIUM = "HUD42"  # HOI Annual Premium (Yearly, Escrow Account)
    
    # Property Tax
    PROPERTY_TAX_AMOUNT = "HUD41"  # Property Tax Amount (Yearly, Escrow Account)


# =============================================================================
# CLOSING CONDITIONS TEMPLATES
# =============================================================================

CLOSING_CONDITION_TEMPLATES = {
    "title_report_expiration": "Title Report Expiration Date should be 60th day of Effective Date of Title Report.",
    "cpl_expiration": "CPL Expiration Date should be 30th day of Effective Date of CPL.",
    "consummation_date": "Consummation date on or After: {closing_date}",
    "pay_hoi_at_closing": "Pay 1 YR Hazard at closing: {hoi_amount}",
    "property_tax_installment": "Property any Tax installment within 60 days of the first payment date: {tax_details} to be paid at closing (if any installment is due within first payment date)",
    "fha_92900_page3": "PTF - Missing Signed Page-3 of Final 92900-A",
    "hoi_renewal": "Current Year HOI Policy is expiring within 2 Months of First Payment date. Expiration Date of Current policy is: {expiration_date}"
}


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_closing_conditions(loan_id: str) -> Dict[str, Any]:
    """
    Validate and generate closing conditions per SOP Step 8.
    
    Validates:
    1. Title Report Expiration (60th day calculation)
    2. CPL Expiration (30th day calculation)
    3. Consummation Date condition
    4. PTF conditions from UW (list for copying)
    5. FHA 92900-A Page 3 condition (if applicable)
    6. Property Tax installment conditions
    7. HOI renewal conditions
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results and generated conditions
    """
    logger.info(f"[CLOSING CONDITIONS] Starting closing conditions validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "conditions_to_add": [],
        "conditions_to_verify": [],
        "ptf_conditions_from_uw": [],
        "calculated_dates": {},
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[CLOSING CONDITIONS] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        state = loan_context.get("state", "")
        county = loan_context.get("county", "")
        loan_type = loan_context.get("loan_type", "").upper()
        
        result["details"].append(f"State: {state}, County: {county}, Loan Type: {loan_type}")
        
        # Read basic fields
        fields = read_fields(loan_id, [
            ClosingConditionFields.PROPERTY_STATE,
            ClosingConditionFields.PROPERTY_COUNTY,
            ClosingConditionFields.LOAN_TYPE,
            ClosingConditionFields.CLOSING_DATE,
        ])
        
        # =====================================================================
        # 1. TITLE REPORT EXPIRATION (60th day)
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Calculating Title Report Expiration...")
        title_expiration = calculate_title_report_expiration(loan_id, fields)
        if title_expiration:
            result["calculated_dates"]["title_report_expiration"] = title_expiration
            result["conditions_to_add"].append({
                "type": "title_report_expiration",
                "description": CLOSING_CONDITION_TEMPLATES["title_report_expiration"],
                "expiration_date": title_expiration.get("expiration_date"),
                "effective_date": title_expiration.get("effective_date"),
                "status": "calculated" if title_expiration.get("effective_date") else "needs_field_id"
            })
        else:
            result["warnings"].append({
                "type": "WARNING",
                "message": "Title Report Effective Date field ID not found - cannot calculate expiration",
                "action_required": "Manually verify Title Report Expiration (60th day from Effective Date)"
            })
        
        # =====================================================================
        # 2. CPL EXPIRATION (30th day)
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Calculating CPL Expiration...")
        cpl_expiration = calculate_cpl_expiration(loan_id, fields)
        if cpl_expiration:
            result["calculated_dates"]["cpl_expiration"] = cpl_expiration
            result["conditions_to_add"].append({
                "type": "cpl_expiration",
                "description": CLOSING_CONDITION_TEMPLATES["cpl_expiration"],
                "expiration_date": cpl_expiration.get("expiration_date"),
                "effective_date": cpl_expiration.get("effective_date"),
                "status": "calculated" if cpl_expiration.get("effective_date") else "needs_field_id"
            })
        else:
            result["warnings"].append({
                "type": "WARNING",
                "message": "CPL Effective Date field ID not found - cannot calculate expiration",
                "action_required": "Manually verify CPL Expiration (30th day from Effective Date)"
            })
        
        # =====================================================================
        # 3. CONSUMMATION DATE
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Checking Consummation Date...")
        consummation_date = get_consummation_date(loan_id, fields)
        if consummation_date:
            result["calculated_dates"]["consummation_date"] = consummation_date
            result["conditions_to_add"].append({
                "type": "consummation_date",
                "description": CLOSING_CONDITION_TEMPLATES["consummation_date"].format(
                    closing_date=consummation_date.get("date", "Closing/Signing date")
                ),
                "date": consummation_date.get("date"),
                "status": "calculated" if consummation_date.get("date") else "needs_field_id"
            })
        else:
            result["warnings"].append({
                "type": "WARNING",
                "message": "Closing Date field ID not found - cannot add Consummation Date condition",
                "action_required": "Manually add Consummation Date condition"
            })
        
        # =====================================================================
        # 4. PTF CONDITIONS FROM UW
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Fetching PTF conditions from UW...")
        try:
            ptf_conditions = list_ptf_conditions(loan_id)
            result["ptf_conditions_from_uw"] = ptf_conditions
            
            if ptf_conditions:
                logger.info(f"[CLOSING CONDITIONS] Found {len(ptf_conditions)} PTF conditions from UW")
                result["conditions_to_verify"].append({
                    "type": "ptf_from_uw",
                    "count": len(ptf_conditions),
                    "message": f"Copy {len(ptf_conditions)} PTF condition(s) from UW Conditions tab to Closing Conditions",
                    "conditions": ptf_conditions
                })
            else:
                logger.info("[CLOSING CONDITIONS] No PTF conditions found in UW Conditions tab")
        except Exception as ptf_error:
            logger.warning(f"[CLOSING CONDITIONS] Could not fetch PTF conditions: {ptf_error}")
            result["warnings"].append({
                "type": "WARNING",
                "message": f"Could not fetch PTF conditions from UW: {str(ptf_error)}",
                "action_required": "Manually check UW Conditions tab for PTF conditions"
            })
        
        # =====================================================================
        # 5. FHA 92900-A PAGE 3 CONDITION
        # =====================================================================
        if "FHA" in loan_type:
            logger.info("[CLOSING CONDITIONS] Checking FHA 92900-A Page 3...")
            fha_page3_check = check_fha_92900_page3(loan_id)
            if fha_page3_check.get("missing"):
                result["conditions_to_add"].append({
                    "type": "fha_92900_page3",
                    "description": CLOSING_CONDITION_TEMPLATES["fha_92900_page3"],
                    "status": "needs_verification",
                    "message": "FHA loan - verify if Signed Page-3 of Final 92900-A is attached"
                })
        
        # =====================================================================
        # 6. PROPERTY TAX INSTALLMENT CONDITIONS
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Checking Property Tax installment conditions...")
        tax_installment = check_property_tax_installment(loan_id, fields)
        if tax_installment.get("needs_condition"):
            result["conditions_to_add"].append({
                "type": "property_tax_installment",
                "description": CLOSING_CONDITION_TEMPLATES["property_tax_installment"].format(
                    tax_details=tax_installment.get("tax_details", "QTR/HALF/Yearly")
                ),
                "status": "calculated" if tax_installment.get("due_within_60_days") else "needs_verification"
            })
        
        # =====================================================================
        # 7. HOI RENEWAL CONDITIONS
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Checking HOI renewal conditions...")
        hoi_renewal = check_hoi_renewal(loan_id, fields)
        if hoi_renewal.get("needs_condition"):
            result["conditions_to_add"].append({
                "type": "hoi_renewal",
                "description": CLOSING_CONDITION_TEMPLATES["hoi_renewal"].format(
                    expiration_date=hoi_renewal.get("expiration_date", "Current policy expiration date")
                ),
                "status": "calculated" if hoi_renewal.get("expiring_within_2_months") else "needs_verification"
            })
        
        # =====================================================================
        # 8. PAY HOI AT CLOSING
        # =====================================================================
        logger.info("[CLOSING CONDITIONS] Checking Pay HOI at closing condition...")
        pay_hoi = check_pay_hoi_at_closing(loan_id, fields)
        if pay_hoi.get("needs_condition"):
            result["conditions_to_add"].append({
                "type": "pay_hoi_at_closing",
                "description": CLOSING_CONDITION_TEMPLATES["pay_hoi_at_closing"].format(
                    hoi_amount=pay_hoi.get("hoi_amount", "Due Amount from Hazard insurance")
                ),
                "status": "calculated" if pay_hoi.get("hoi_amount") else "needs_field_id"
            })
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        result["status"] = "complete"
        result["details"].append(f"Conditions to add: {len(result['conditions_to_add'])}")
        result["details"].append(f"PTF conditions from UW: {len(result['ptf_conditions_from_uw'])}")
        result["details"].append(f"Warnings: {len(result['warnings'])}")
        
        logger.info("\n" + "="*80)
        logger.info(f"[CLOSING CONDITIONS] ✅ Validation complete")
        logger.info(f"[CLOSING CONDITIONS] Conditions to add: {len(result['conditions_to_add'])}")
        logger.info(f"[CLOSING CONDITIONS] PTF from UW: {len(result['ptf_conditions_from_uw'])}")
        logger.info("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"[CLOSING CONDITIONS] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_title_report_expiration(loan_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculate Title Report Expiration (60th day from Effective Date).
    
    Returns:
        Dictionary with expiration_date and effective_date, or None if field ID not found
    """
    # TODO: Need Title Report Effective Date field ID
    if ClosingConditionFields.TITLE_REPORT_EFFECTIVE_DATE:
        effective_date_str = fields.get(ClosingConditionFields.TITLE_REPORT_EFFECTIVE_DATE)
        if effective_date_str:
            try:
                effective_date = datetime.strptime(effective_date_str, "%Y-%m-%d")
                expiration_date = effective_date + timedelta(days=60)
                return {
                    "effective_date": effective_date_str,
                    "expiration_date": expiration_date.strftime("%Y-%m-%d")
                }
            except Exception as e:
                logger.warning(f"[CLOSING CONDITIONS] Error parsing Title Report Effective Date: {e}")
    
    return None


def calculate_cpl_expiration(loan_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculate CPL Expiration (30th day from Effective Date).
    
    Returns:
        Dictionary with expiration_date and effective_date, or None if field ID not found
    """
    # TODO: Need CPL Effective Date field ID
    if ClosingConditionFields.CPL_EFFECTIVE_DATE:
        effective_date_str = fields.get(ClosingConditionFields.CPL_EFFECTIVE_DATE)
        if effective_date_str:
            try:
                effective_date = datetime.strptime(effective_date_str, "%Y-%m-%d")
                expiration_date = effective_date + timedelta(days=30)
                return {
                    "effective_date": effective_date_str,
                    "expiration_date": expiration_date.strftime("%Y-%m-%d")
                }
            except Exception as e:
                logger.warning(f"[CLOSING CONDITIONS] Error parsing CPL Effective Date: {e}")
    
    return None


def get_consummation_date(loan_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get Consummation Date (Closing/Signing date).
    
    Returns:
        Dictionary with date, or None if field ID not found
    """
    # TODO: Need Closing Date field ID
    if ClosingConditionFields.CLOSING_DATE:
        closing_date = fields.get(ClosingConditionFields.CLOSING_DATE)
        if closing_date:
            return {"date": closing_date}
    
    return None


def check_fha_92900_page3(loan_id: str) -> Dict[str, Any]:
    """
    Check if FHA 92900-A Page 3 is attached.
    
    Returns:
        Dictionary with missing flag
    """
    # TODO: Need to check if document is attached in Encompass
    # For now, return needs verification
    return {
        "missing": None,  # Unknown - needs manual verification
        "needs_verification": True
    }


def check_property_tax_installment(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if Property Tax installment is due within 60 days of first payment date.
    
    Returns:
        Dictionary with needs_condition flag
    """
    # TODO: Need First Payment Date and Property Tax installment dates
    if ClosingConditionFields.FIRST_PAYMENT_DATE:
        first_payment_date_str = fields.get(ClosingConditionFields.FIRST_PAYMENT_DATE)
        if first_payment_date_str:
            try:
                first_payment_date = datetime.strptime(first_payment_date_str, "%Y-%m-%d")
                # Check if any tax installment is within 60 days
                # This would require tax installment dates from Title Report or Tax Summary
                return {
                    "needs_condition": None,  # Unknown - needs manual verification
                    "due_within_60_days": None,
                    "tax_details": "QTR/HALF/Yearly"
                }
            except Exception as e:
                logger.warning(f"[CLOSING CONDITIONS] Error parsing First Payment Date: {e}")
    
    return {
        "needs_condition": None,  # Unknown - needs field IDs
        "due_within_60_days": None
    }


def check_hoi_renewal(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if HOI policy is expiring within 2 months of first payment date.
    
    Returns:
        Dictionary with needs_condition flag
    """
    # TODO: Need HOI Expiration Date and First Payment Date
    if ClosingConditionFields.HOI_EXPIRATION_DATE and ClosingConditionFields.FIRST_PAYMENT_DATE:
        hoi_exp_str = fields.get(ClosingConditionFields.HOI_EXPIRATION_DATE)
        first_payment_str = fields.get(ClosingConditionFields.FIRST_PAYMENT_DATE)
        
        if hoi_exp_str and first_payment_str:
            try:
                hoi_exp_date = datetime.strptime(hoi_exp_str, "%Y-%m-%d")
                first_payment_date = datetime.strptime(first_payment_str, "%Y-%m-%d")
                
                # Check if expiring within 2 months (60 days) of first payment
                days_until_exp = (hoi_exp_date - first_payment_date).days
                if 0 <= days_until_exp <= 60:
                    return {
                        "needs_condition": True,
                        "expiring_within_2_months": True,
                        "expiration_date": hoi_exp_str
                    }
            except Exception as e:
                logger.warning(f"[CLOSING CONDITIONS] Error checking HOI renewal: {e}")
    
    return {
        "needs_condition": None,  # Unknown - needs field IDs
        "expiring_within_2_months": None
    }


def check_pay_hoi_at_closing(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if Pay 1 YR Hazard at closing condition is needed.
    
    Returns:
        Dictionary with needs_condition flag and hoi_amount
    """
    # TODO: Need HOI Annual Premium
    if ClosingConditionFields.HOI_ANNUAL_PREMIUM:
        hoi_amount = fields.get(ClosingConditionFields.HOI_ANNUAL_PREMIUM)
        if hoi_amount:
            return {
                "needs_condition": True,
                "hoi_amount": hoi_amount
            }
    
    return {
        "needs_condition": None,  # Unknown - needs field ID
        "hoi_amount": None
    }


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_closing_conditions",
    "calculate_title_report_expiration",
    "calculate_cpl_expiration",
    "get_consummation_date",
    "check_fha_92900_page3",
    "check_property_tax_installment",
    "check_hoi_renewal",
    "check_pay_hoi_at_closing",
]

