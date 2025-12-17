"""
Closing Disclosure (CD) Page Validation Tools for Phase 3.

Implements SOP Steps 21-25:
- CD Page 1: Changed Circumstance (COC) tracking
- CD Page 2: Fee sections validation
- CD Page 3: Transaction summaries
- CD Page 4: Loan disclosures (requires manual field mapping)
- CD Page 5: Loan calculations and contacts

Uses confirmed fields from master_field_data.csv.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS (All confirmed from master_field_data.csv)
# =============================================================================

class CDPageFields:
    """Encompass field IDs for CD page validation."""
    
    # CD Page 1 - Changed Circumstance tracking
    COC_CHECKBOX = "CD1.X61"  # Changed Circumstance Checkbox
    COC_DATE = "CD1.X62"  # Changed Circumstance Received Date
    TOLERANCE_CURE = "CD1.X57"  # Tolerance Cure flag
    REVISED_CD_DUE_DATE = "CD1.X63"  # Revised CD Due Date
    TOTAL_CASH_TO_CLOSE = "CD1.X69"  # Total Cash To Close
    REASON_CHANGED_CIRCUMSTANCE = "CD1.X70"  # Reason flags
    
    # CD Page 3 - Transaction summaries
    CASH_TO_CLOSE = "CD3.X23"  # Due from Borrower
    FINAL_CASH_TO_CLOSE = "CD3.X45"  # Final Cash To Close
    CLOSING_COSTS_PAID_AT_CLOSING = "CD3.X1"  # J line
    CLOSING_COSTS_AT_CLOSING_J = "CD3.X46"  # J total
    TOTAL_CLOSING_COST_J = "CD3.X82"  # Section J
    CLOSING_COSTS_BEFORE_CLOSING = "CD3.X83"  # Before closing
    TOTAL_PAYOFFS_K = "CD3.X84"  # Section K
    CD3_CASH_TO_CLOSE = "CD3.X85"  # CD3 calculation
    CD3_CASH_FROM_TO_BORROWER = "CD3.X86"  # From/To borrower


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


def parse_date(date_str: Any) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str or date_str == "":
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        # Try common date formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


# =============================================================================
# CD PAGE 1 VALIDATION - Changed Circumstance (COC)
# =============================================================================

def validate_changed_circumstance(loan_id: str) -> Dict[str, Any]:
    """
    Validate Changed Circumstance (COC) CD requirements.
    
    Per SOP Step 21:
    - COC CD required when certain changes occur after initial CD
    - 3-day waiting period required if APR increases > 0.125% or loan product changes
    - NO waiting period if APR decreases or no material changes
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with COC validation results
    """
    logger.info(f"[COC VALIDATION] Starting Changed Circumstance validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "coc_issued": False,
        "coc_date": None,
        "warnings": [],
        "details": []
    }
    
    try:
        # Read COC-related fields
        logger.info("[COC VALIDATION] Reading COC fields...")
        fields = read_fields(loan_id, [
            CDPageFields.COC_CHECKBOX,
            CDPageFields.COC_DATE,
            CDPageFields.TOLERANCE_CURE,
            CDPageFields.REVISED_CD_DUE_DATE,
            CDPageFields.REASON_CHANGED_CIRCUMSTANCE,
        ])
        
        if not fields:
            logger.warning("[COC VALIDATION] No fields returned")
            result["status"] = "error"
            result["details"].append("Unable to read COC fields from Encompass")
            return result
        
        # Extract COC tracking fields
        coc_checkbox = fields.get(CDPageFields.COC_CHECKBOX)
        coc_date = fields.get(CDPageFields.COC_DATE)
        tolerance_cure = fields.get(CDPageFields.TOLERANCE_CURE)
        revised_due_date = fields.get(CDPageFields.REVISED_CD_DUE_DATE)
        coc_reason = fields.get(CDPageFields.REASON_CHANGED_CIRCUMSTANCE)
        
        # Determine if COC CD was issued
        result["coc_issued"] = bool(coc_checkbox or coc_date)
        result["coc_date"] = coc_date
        
        logger.info(f"[COC VALIDATION] COC Checkbox: {coc_checkbox}")
        logger.info(f"[COC VALIDATION] COC Date: {coc_date}")
        logger.info(f"[COC VALIDATION] Tolerance Cure: {tolerance_cure}")
        
        # Check for consistency
        if coc_checkbox and not coc_date:
            result["warnings"].append({
                "type": "WARNING",
                "severity": "MEDIUM",
                "field": "CD1.X62",
                "message": "COC CD checkbox is checked but COC date is not populated",
                "action_required": "Populate COC CD Received Date (CD1.X62)",
                "sop_reference": "Step 21 - CD Page 1"
            })
        
        if coc_date and not coc_checkbox:
            result["warnings"].append({
                "type": "WARNING",
                "severity": "MEDIUM",
                "field": "CD1.X61",
                "message": "COC CD date is populated but checkbox is not checked",
                "action_required": "Check COC CD Changed Circumstance checkbox (CD1.X61)",
                "sop_reference": "Step 21 - CD Page 1"
            })
        
        # If COC issued and tolerance cure applied, validate consistency
        if result["coc_issued"] and tolerance_cure:
            result["details"].append("COC CD issued with tolerance cure applied")
            logger.info("[COC VALIDATION] COC CD with tolerance cure detected")
        
        # Status determination
        if len(result["warnings"]) > 0:
            result["status"] = "warnings_found"
            logger.warning(f"[COC VALIDATION] Found {len(result['warnings'])} warnings")
        else:
            result["status"] = "compliant"
            logger.info("[COC VALIDATION] ✅ COC tracking compliant")
        
        result["details"].append(f"COC CD issued: {'Yes' if result['coc_issued'] else 'No'}")
        if result["coc_issued"]:
            result["details"].append(f"COC Date: {coc_date}")
        
        return result
        
    except Exception as e:
        logger.error(f"[COC VALIDATION] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# CD PAGE 3 VALIDATION - Transaction Summaries
# =============================================================================

def validate_cd_page_3(loan_id: str) -> Dict[str, Any]:
    """
    Validate CD Page 3 transaction summaries.
    
    Per SOP Step 23:
    - Section K: Due from Borrower at Closing
    - Section M: Due to Seller at Closing
    - Cash to Close calculations
    - Payoffs and payments
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with CD Page 3 validation results
    """
    logger.info(f"[CD PAGE 3] Starting validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "violations": [],
        "cash_to_close": 0.0,
        "details": []
    }
    
    try:
        # Read CD Page 3 fields
        logger.info("[CD PAGE 3] Reading transaction summary fields...")
        fields = read_fields(loan_id, [
            CDPageFields.CASH_TO_CLOSE,
            CDPageFields.FINAL_CASH_TO_CLOSE,
            CDPageFields.CLOSING_COSTS_PAID_AT_CLOSING,
            CDPageFields.CLOSING_COSTS_AT_CLOSING_J,
            CDPageFields.TOTAL_CLOSING_COST_J,
            CDPageFields.CLOSING_COSTS_BEFORE_CLOSING,
            CDPageFields.TOTAL_PAYOFFS_K,
            CDPageFields.CD3_CASH_TO_CLOSE,
            CDPageFields.CD3_CASH_FROM_TO_BORROWER,
        ])
        
        if not fields:
            logger.warning("[CD PAGE 3] No fields returned")
            result["status"] = "error"
            result["details"].append("Unable to read CD Page 3 fields from Encompass")
            return result
        
        # Extract values
        cash_to_close = safe_float(fields.get(CDPageFields.CASH_TO_CLOSE))
        final_cash_to_close = safe_float(fields.get(CDPageFields.FINAL_CASH_TO_CLOSE))
        closing_costs_at_closing = safe_float(fields.get(CDPageFields.CLOSING_COSTS_AT_CLOSING))
        total_closing_cost_j = safe_float(fields.get(CDPageFields.TOTAL_CLOSING_COST_J))
        total_payoffs_k = safe_float(fields.get(CDPageFields.TOTAL_PAYOFFS_K))
        
        result["cash_to_close"] = cash_to_close
        
        logger.info(f"[CD PAGE 3] Cash To Close: {format_currency(cash_to_close)}")
        logger.info(f"[CD PAGE 3] Final Cash To Close: {format_currency(final_cash_to_close)}")
        logger.info(f"[CD PAGE 3] Total Closing Cost J: {format_currency(total_closing_cost_j)}")
        logger.info(f"[CD PAGE 3] Total Payoffs K: {format_currency(total_payoffs_k)}")
        
        # Check for consistency between cash to close fields
        if abs(cash_to_close - final_cash_to_close) > 0.01:  # Allow $0.01 rounding
            result["violations"].append({
                "type": "WARNING",
                "severity": "MEDIUM",
                "category": "CD Page 3 Inconsistency",
                "message": f"Cash To Close mismatch: CD3.X23 = {format_currency(cash_to_close)}, CD3.X45 = {format_currency(final_cash_to_close)}",
                "details": {
                    "cd3_x23": format_currency(cash_to_close),
                    "cd3_x45": format_currency(final_cash_to_close),
                    "difference": format_currency(abs(cash_to_close - final_cash_to_close))
                },
                "action_required": "Verify Cash to Close calculation on CD Page 3",
                "fields_affected": ["CD3.X23", "CD3.X45"],
                "sop_reference": "Step 23 - CD Page 3"
            })
        
        # Check for missing or zero cash to close (unusual)
        if cash_to_close == 0.0 and total_closing_cost_j > 0.0:
            result["violations"].append({
                "type": "WARNING",
                "severity": "LOW",
                "category": "CD Page 3 Warning",
                "message": "Cash To Close is $0.00 but Total Closing Costs are greater than $0.00",
                "details": {
                    "cash_to_close": format_currency(cash_to_close),
                    "total_closing_costs": format_currency(total_closing_cost_j)
                },
                "action_required": "Verify Cash to Close calculation is correct",
                "fields_affected": ["CD3.X23", "CD3.X82"],
                "sop_reference": "Step 23 - CD Page 3"
            })
        
        # Status determination
        if len(result["violations"]) > 0:
            result["status"] = "warnings_found"
            logger.warning(f"[CD PAGE 3] Found {len(result['violations'])} warnings")
        else:
            result["status"] = "compliant"
            logger.info("[CD PAGE 3] ✅ Transaction summaries appear correct")
        
        result["details"].append(f"Cash To Close: {format_currency(cash_to_close)}")
        result["details"].append(f"Total Closing Costs: {format_currency(total_closing_cost_j)}")
        result["details"].append(f"Total Payoffs: {format_currency(total_payoffs_k)}")
        
        return result
        
    except Exception as e:
        logger.error(f"[CD PAGE 3] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# CD PAGE 4 VALIDATION - Loan Disclosures (Field IDs Confirmed)
# =============================================================================

class CDPage4Fields:
    """Encompass field IDs for CD Page 4 validation (confirmed from Encompass)."""
    
    # CD Page 4 - Loan Disclosures (Confirmed)
    LATE_PAYMENT_PCT = "674"  # Late payment percentage
    ASSUMPTION = "LE3.X12"  # Assumption clause
    DEMAND_FEATURE = "663"  # Demand feature
    NEGATIVE_AMORTIZATION = "CD4.X2"  # Negative amortization


def validate_cd_page_4(loan_id: str, loan_type: str, amort_type: str) -> Dict[str, Any]:
    """
    Validate CD Page 4 disclosure fields.
    
    Per SOP Step 24:
    - Late Payment: 4% for FHA/VA/USDA, 5% for Conventional
    - Assumption: Varies by loan type and amortization
    - Demand Feature: Always "does not have a demand feature"
    - Negative Amortization: Always "do not have a negative amortization feature"
    
    Args:
        loan_id: Encompass loan GUID
        loan_type: Loan type (FHA, VA, USDA, Conventional)
        amort_type: Amortization type (Fixed, ARM, etc.)
        
    Returns:
        Dictionary with validation results and PTF conditions
    """
    logger.info(f"[CD PAGE 4] Starting validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "loan_type": loan_type,
        "amort_type": amort_type,
        "violations": [],
        "details": []
    }
    
    try:
        # Read CD Page 4 fields
        logger.info("[CD PAGE 4] Reading loan disclosure fields...")
        fields = read_fields(loan_id, [
            CDPage4Fields.LATE_PAYMENT_PCT,
            CDPage4Fields.ASSUMPTION,
            CDPage4Fields.DEMAND_FEATURE,
            CDPage4Fields.NEGATIVE_AMORTIZATION,
        ])
        
        if not fields:
            logger.warning("[CD PAGE 4] No fields returned from Encompass")
            result["status"] = "error"
            result["details"].append("Unable to read CD Page 4 fields from Encompass")
            return result
        
        # Extract values
        late_payment_pct = safe_float(fields.get(CDPage4Fields.LATE_PAYMENT_PCT))
        assumption = str(fields.get(CDPage4Fields.ASSUMPTION, "")).strip()
        demand_feature = str(fields.get(CDPage4Fields.DEMAND_FEATURE, "")).strip()
        negative_amort = str(fields.get(CDPage4Fields.NEGATIVE_AMORTIZATION, "")).strip()
        
        logger.info(f"[CD PAGE 4] Late Payment %: {late_payment_pct}%")
        logger.info(f"[CD PAGE 4] Assumption: {assumption}")
        logger.info(f"[CD PAGE 4] Demand Feature: {demand_feature}")
        logger.info(f"[CD PAGE 4] Negative Amortization: {negative_amort}")
        
        # =====================================================================
        # LATE PAYMENT FEE VALIDATION
        # =====================================================================
        expected_late_fee_pct = 4.0 if loan_type in ["FHA", "VA", "USDA"] else 5.0
        
        if abs(late_payment_pct - expected_late_fee_pct) > 0.01:  # Allow 0.01% rounding
            result["violations"].append({
                "type": "PTF",
                "severity": "MEDIUM",
                "category": "CD Page 4 Disclosure Error",
                "field_id": CDPage4Fields.LATE_PAYMENT_PCT,
                "field_name": "Late Payment Percentage",
                "message": f"Late payment fee is {late_payment_pct}%, should be {expected_late_fee_pct}% for {loan_type} loans",
                "details": {
                    "current_value": f"{late_payment_pct}%",
                    "expected_value": f"{expected_late_fee_pct}%",
                    "loan_type": loan_type,
                    "difference": f"{abs(late_payment_pct - expected_late_fee_pct)}%"
                },
                "action_required": f"Update Late Payment percentage to {expected_late_fee_pct}% on CD Page 4",
                "fields_affected": [CDPage4Fields.LATE_PAYMENT_PCT],
                "sop_reference": "Step 24 - CD Page 4",
                "compliance_issue": f"Late payment fee must be {expected_late_fee_pct}% for {loan_type} loans per SOP"
            })
            logger.warning(f"[CD PAGE 4] ⚠️  Late payment % incorrect: {late_payment_pct}% (expected {expected_late_fee_pct}%)")
        else:
            logger.info(f"[CD PAGE 4] ✅ Late payment % correct: {late_payment_pct}%")
        
        # =====================================================================
        # ASSUMPTION CLAUSE VALIDATION
        # =====================================================================
        # Determine expected assumption based on loan type and amortization
        if loan_type in ["FHA", "VA", "USDA"] and amort_type == "Fixed":
            expected_assumption = "will allow"
        elif loan_type == "Conventional" and amort_type == "Fixed":
            expected_assumption = "will not allow"
        elif loan_type == "Conventional" and amort_type == "ARM":
            expected_assumption = "will allow"  # For specific investors
        else:
            expected_assumption = None  # Unknown case - skip validation
        
        if expected_assumption:
            assumption_lower = assumption.lower()
            if expected_assumption == "will allow":
                if "will not allow" in assumption_lower or "not allow" in assumption_lower:
                    result["violations"].append({
                        "type": "PTF",
                        "severity": "MEDIUM",
                        "category": "CD Page 4 Disclosure Error",
                        "field_id": CDPage4Fields.ASSUMPTION,
                        "field_name": "Assumption Clause",
                        "message": f"Assumption clause is '{assumption}', should be 'will allow' for {loan_type} {amort_type} loans",
                        "details": {
                            "current_value": assumption,
                            "expected_value": "will allow",
                            "loan_type": loan_type,
                            "amort_type": amort_type
                        },
                        "action_required": "Update Assumption clause to 'will allow' on CD Page 4",
                        "fields_affected": [CDPage4Fields.ASSUMPTION],
                        "sop_reference": "Step 24 - CD Page 4",
                        "compliance_issue": f"Assumption must be 'will allow' for {loan_type} {amort_type} loans per SOP"
                    })
                    logger.warning(f"[CD PAGE 4] ⚠️  Assumption clause incorrect: {assumption}")
                else:
                    logger.info(f"[CD PAGE 4] ✅ Assumption clause correct: {assumption}")
            elif expected_assumption == "will not allow":
                if "will allow" in assumption_lower and "not" not in assumption_lower:
                    result["violations"].append({
                        "type": "PTF",
                        "severity": "MEDIUM",
                        "category": "CD Page 4 Disclosure Error",
                        "field_id": CDPage4Fields.ASSUMPTION,
                        "field_name": "Assumption Clause",
                        "message": f"Assumption clause is '{assumption}', should be 'will not allow' for {loan_type} {amort_type} loans",
                        "details": {
                            "current_value": assumption,
                            "expected_value": "will not allow",
                            "loan_type": loan_type,
                            "amort_type": amort_type
                        },
                        "action_required": "Update Assumption clause to 'will not allow' on CD Page 4",
                        "fields_affected": [CDPage4Fields.ASSUMPTION],
                        "sop_reference": "Step 24 - CD Page 4",
                        "compliance_issue": f"Assumption must be 'will not allow' for {loan_type} {amort_type} loans per SOP"
                    })
                    logger.warning(f"[CD PAGE 4] ⚠️  Assumption clause incorrect: {assumption}")
                else:
                    logger.info(f"[CD PAGE 4] ✅ Assumption clause correct: {assumption}")
        
        # =====================================================================
        # DEMAND FEATURE VALIDATION
        # =====================================================================
        demand_lower = demand_feature.lower()
        if "does not have" not in demand_lower or "demand feature" not in demand_lower:
            result["violations"].append({
                "type": "PTF",
                "severity": "LOW",
                "category": "CD Page 4 Disclosure Error",
                "field_id": CDPage4Fields.DEMAND_FEATURE,
                "field_name": "Demand Feature",
                "message": f"Demand feature is '{demand_feature}', should be 'does not have a demand feature'",
                "details": {
                    "current_value": demand_feature,
                    "expected_value": "does not have a demand feature"
                },
                "action_required": "Update Demand Feature to 'does not have a demand feature' on CD Page 4",
                "fields_affected": [CDPage4Fields.DEMAND_FEATURE],
                "sop_reference": "Step 24 - CD Page 4",
                "compliance_issue": "Demand feature should always be 'does not have a demand feature' per SOP"
            })
            logger.warning(f"[CD PAGE 4] ⚠️  Demand feature incorrect: {demand_feature}")
        else:
            logger.info(f"[CD PAGE 4] ✅ Demand feature correct: {demand_feature}")
        
        # =====================================================================
        # NEGATIVE AMORTIZATION VALIDATION
        # =====================================================================
        neg_amort_lower = negative_amort.lower()
        if "do not have" not in neg_amort_lower or "negative amortization" not in neg_amort_lower:
            result["violations"].append({
                "type": "PTF",
                "severity": "LOW",
                "category": "CD Page 4 Disclosure Error",
                "field_id": CDPage4Fields.NEGATIVE_AMORTIZATION,
                "field_name": "Negative Amortization",
                "message": f"Negative amortization is '{negative_amort}', should be 'do not have a negative amortization feature'",
                "details": {
                    "current_value": negative_amort,
                    "expected_value": "do not have a negative amortization feature"
                },
                "action_required": "Update Negative Amortization to 'do not have a negative amortization feature' on CD Page 4",
                "fields_affected": [CDPage4Fields.NEGATIVE_AMORTIZATION],
                "sop_reference": "Step 24 - CD Page 4",
                "compliance_issue": "Negative amortization should always be 'do not have a negative amortization feature' per SOP"
            })
            logger.warning(f"[CD PAGE 4] ⚠️  Negative amortization incorrect: {negative_amort}")
        else:
            logger.info(f"[CD PAGE 4] ✅ Negative amortization correct: {negative_amort}")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        if len(result["violations"]) > 0:
            result["status"] = "violations_found"
            logger.warning(f"[CD PAGE 4] Found {len(result['violations'])} disclosure violations")
        else:
            result["status"] = "compliant"
            logger.info("[CD PAGE 4] ✅ All CD Page 4 disclosures correct")
        
        # Add summary details
        result["details"].append(f"Late Payment: {late_payment_pct}% ({'Correct' if abs(late_payment_pct - expected_late_fee_pct) <= 0.01 else 'Incorrect'})")
        result["details"].append(f"Assumption: {assumption[:50]}...")
        result["details"].append(f"Demand Feature: {'Correct' if 'does not have' in demand_lower else 'Incorrect'}")
        result["details"].append(f"Negative Amortization: {'Correct' if 'do not have' in neg_amort_lower else 'Incorrect'}")
        
        return result
        
    except Exception as e:
        logger.error(f"[CD PAGE 4] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_changed_circumstance",
    "validate_cd_page_3",
    "validate_cd_page_4",
]

