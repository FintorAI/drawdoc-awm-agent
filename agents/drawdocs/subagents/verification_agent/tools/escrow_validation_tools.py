"""
Escrow & Financial Validation Tools for DrawDocs Verification Agent.

Per SOP Step 19 (Aggregate Escrow Account):
- Calculate state-specific monthly property taxes
- Calculate monthly insurance premiums
- Validate cushion months (2 for taxes/insurance, 0 for MI)
- Calculate initial escrow balance
- Validate impound requirements (FHA/VA require impounds, Conventional >80% LTV requires impounds)

Generates PTF conditions if:
- Monthly tax calculation doesn't match UW approval
- Impounds required but not set up
- Escrow balance calculation errors
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from agents.drawdocs.tools.primitives import read_fields, add_ptf_condition, log_issue

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR ESCROW
# =============================================================================

class EscrowFields:
    """
    Encompass field IDs for escrow validation.
    
    ✅ = Confirmed from master_field_data.csv
    ❌ = Still need to find
    """
    
    # Loan Context
    LOAN_AMOUNT = "1109"  # ✅
    LOAN_TYPE = "1172"  # ✅ Conventional, FHA, VA, USDA
    LOAN_PURPOSE = "19"  # ✅ Purchase, Refinance
    LTV = "353"  # ✅
    PROPERTY_STATE = "14"  # ✅
    
    # Property
    PURCHASE_PRICE = "136"  # ✅ Subject Property Purchase Price
    APPRAISED_VALUE = "356"  # ✅
    
    # Dates
    CLOSING_DATE = "748"  # ✅
    FIRST_PAYMENT_DATE = "682"  # ✅ First Pymt Date
    DISBURSEMENT_DATE = "2553"  # ✅
    
    # Monthly Expenses (Proposed)
    MONTHLY_TAX = "1405"  # ✅ Expenses Proposed Taxes
    MONTHLY_HOI = "230"  # ✅ Expenses Proposed Haz Ins
    MONTHLY_FLOOD = "235"  # ✅ Fees Flood Ins Per Mo
    MONTHLY_MI = "232"  # ✅ Expenses Proposed Mtg Ins (from previous list)
    
    # Yearly/Annual Amounts
    YEARLY_TAX = None  # ❌ Need to find
    YEARLY_HOI = "HUD42"  # ✅ From Phase 1
    YEARLY_FLOOD = "HUD44"  # ✅ From Phase 1
    
    # Reserve/Cushion Months
    TAX_RESERVE_MONTHS = "1386"  # ✅ Fees Tax # of Mos Reserve Required
    HOI_RESERVE_MONTHS = "1387"  # ✅ Fees Hazard Ins # of Mos Reserve Required
    FLOOD_RESERVE_MONTHS = "1388"  # ✅ Fees Flood Ins # of Mos Reserve Required
    MI_RESERVE_MONTHS = None  # ❌ Need to find (should be 0)
    
    # Impound Settings
    IMPOUND_TYPE = "2294"  # ✅ Impound Types
    IMPOUNDS_WAIVED = "2293"  # ✅ Impounds Waived
    
    # Initial Escrow Balance
    INITIAL_ESCROW_BALANCE = None  # ❌ Need to find
    AGGREGATE_ESCROW_ADJUSTMENT = None  # ❌ Need to find (always negative or zero)
    
    # Tax Certificate Info (for CO mill levy calculation)
    MILL_LEVY_RATE = None  # ❌ Need to find (CO only)
    ASSESSED_VALUE = None  # ❌ Need to find (CO only)


# =============================================================================
# STATE-SPECIFIC TAX RATES
# =============================================================================

class StateTaxRates:
    """State-specific property tax calculation rates per SOP Step 19."""
    
    # New Construction / Builder Loans
    NEVADA_NEW_CONSTRUCTION = 0.01  # 1% of sales price
    ARIZONA_NEW_CONSTRUCTION = 0.01  # 1% of sales price
    CALIFORNIA_NEW_CONSTRUCTION = 0.0125  # 1.25% of sales price
    COLORADO_NEW_CONSTRUCTION = 0.01  # 1% of sales price OR mill levy (whichever UW uses)
    
    # Standard calculation: Use higher of tax summary or calculation


# =============================================================================
# STATE-SPECIFIC TAX CALCULATOR
# =============================================================================

def calculate_monthly_property_tax(
    loan_id: str,
    state: str,
    property_type: str = "Resale",  # "New Construction", "Builder", or "Resale"
    sales_price: Optional[float] = None,
    mill_levy_rate: Optional[float] = None,
    tax_summary_annual: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate monthly property tax using state-specific formulas.
    
    Per SOP Step 19:
    - NV/AZ New Construction: 1% of sales price ÷ 12
    - CA New Construction/Resale: 1.25% of sales price ÷ 12 (vs tax summary, whichever higher)
    - CO New Construction: Either mill levy or 1% of sales price (whichever UW uses)
    - Other states/Resale: Use tax summary amount ÷ 12
    
    Args:
        loan_id: Encompass loan GUID
        state: 2-letter state code (e.g., "NV", "CA", "CO")
        property_type: "New Construction", "Builder", or "Resale"
        sales_price: Purchase price or appraised value
        mill_levy_rate: Mill levy rate (CO only, per 1000)
        tax_summary_annual: Annual tax amount from tax certificate/summary
        
    Returns:
        Dictionary with calculation results:
        {
            "monthly_tax": float,
            "annual_tax": float,
            "calculation_method": str,
            "formula_used": str,
            "compared_to_tax_summary": bool,
            "tax_summary_amount": Optional[float],
            "warnings": List[str]
        }
    """
    logger.info(f"[ESCROW-TAX] Calculating monthly property tax for {state} ({property_type})")
    
    result = {
        "monthly_tax": None,
        "annual_tax": None,
        "calculation_method": None,
        "formula_used": None,
        "compared_to_tax_summary": False,
        "tax_summary_amount": tax_summary_annual,
        "warnings": []
    }
    
    state = state.upper().strip()
    is_new_construction = property_type.lower() in ["new construction", "builder", "under construction"]
    
    # =========================================================================
    # NEW CONSTRUCTION / BUILDER CALCULATIONS
    # =========================================================================
    
    if is_new_construction:
        if not sales_price:
            result["warnings"].append("Sales price not provided - cannot calculate tax for new construction")
            return result
        
        # Nevada & Arizona
        if state in ["NV", "AZ"]:
            annual_tax = sales_price * StateTaxRates.NEVADA_NEW_CONSTRUCTION
            monthly_tax = annual_tax / 12
            result["calculation_method"] = f"{state} New Construction: 1% of sales price"
            result["formula_used"] = f"${sales_price:,.2f} × 1% ÷ 12 = ${monthly_tax:,.2f}"
        
        # California
        elif state == "CA":
            calculated_annual = sales_price * StateTaxRates.CALIFORNIA_NEW_CONSTRUCTION
            calculated_monthly = calculated_annual / 12
            
            # CA: Use whichever is HIGHER (calculation vs tax summary)
            if tax_summary_annual:
                tax_summary_monthly = tax_summary_annual / 12
                if tax_summary_monthly > calculated_monthly:
                    monthly_tax = tax_summary_monthly
                    annual_tax = tax_summary_annual
                    result["calculation_method"] = "CA: Tax Summary (higher than 1.25% calculation)"
                    result["formula_used"] = f"Tax Summary ${tax_summary_annual:,.2f} ÷ 12 = ${monthly_tax:,.2f}"
                    result["compared_to_tax_summary"] = True
                else:
                    monthly_tax = calculated_monthly
                    annual_tax = calculated_annual
                    result["calculation_method"] = "CA New Construction: 1.25% of sales price (higher)"
                    result["formula_used"] = f"${sales_price:,.2f} × 1.25% ÷ 12 = ${monthly_tax:,.2f}"
                    result["compared_to_tax_summary"] = True
            else:
                monthly_tax = calculated_monthly
                annual_tax = calculated_annual
                result["calculation_method"] = "CA New Construction: 1.25% of sales price"
                result["formula_used"] = f"${sales_price:,.2f} × 1.25% ÷ 12 = ${monthly_tax:,.2f}"
        
        # Colorado
        elif state == "CO":
            # CO: Either mill levy OR 1% of sales price (whichever UW uses)
            if mill_levy_rate:
                # Mill Levy Calculation:
                # 1. Assessed value = appraisal value × 7.96%
                # 2. Mill rate per dollar = mill_levy_rate / 1000
                # 3. Total tax = assessed value × mill rate per dollar
                # 4. Monthly = total tax / 12
                assessed_value = sales_price * 0.0796
                mill_rate_per_dollar = mill_levy_rate / 1000
                annual_tax = assessed_value * mill_rate_per_dollar
                monthly_tax = annual_tax / 12
                result["calculation_method"] = "CO Mill Levy Calculation"
                result["formula_used"] = (
                    f"Assessed: ${sales_price:,.2f} × 7.96% = ${assessed_value:,.2f}, "
                    f"Mill Rate: {mill_levy_rate} / 1000 = {mill_rate_per_dollar:.6f}, "
                    f"Tax: ${assessed_value:,.2f} × {mill_rate_per_dollar:.6f} = ${annual_tax:,.2f} ÷ 12 = ${monthly_tax:,.2f}"
                )
            else:
                # Fallback: 1% of sales price
                annual_tax = sales_price * StateTaxRates.COLORADO_NEW_CONSTRUCTION
                monthly_tax = annual_tax / 12
                result["calculation_method"] = "CO New Construction: 1% of sales price (fallback)"
                result["formula_used"] = f"${sales_price:,.2f} × 1% ÷ 12 = ${monthly_tax:,.2f}"
                result["warnings"].append("Mill levy rate not provided - using 1% fallback")
    
    # =========================================================================
    # RESALE / NON-BUILDER CALCULATIONS
    # =========================================================================
    
    else:
        # Resale properties: Use tax summary/certificate
        if tax_summary_annual:
            monthly_tax = tax_summary_annual / 12
            annual_tax = tax_summary_annual
            result["calculation_method"] = "Tax Summary / Certificate"
            result["formula_used"] = f"${tax_summary_annual:,.2f} ÷ 12 = ${monthly_tax:,.2f}"
        else:
            result["warnings"].append("Tax summary not provided - cannot calculate monthly tax for resale property")
            return result
        
        # CA Resale: Still compare to 1.25% calculation and use higher
        if state == "CA" and sales_price:
            calculated_annual = sales_price * 0.0125
            calculated_monthly = calculated_annual / 12
            
            if calculated_monthly > monthly_tax:
                monthly_tax = calculated_monthly
                annual_tax = calculated_annual
                result["calculation_method"] = "CA: 1.25% calculation (higher than tax summary)"
                result["formula_used"] = f"${sales_price:,.2f} × 1.25% ÷ 12 = ${monthly_tax:,.2f} (vs ${tax_summary_annual:,.2f} tax summary)"
                result["compared_to_tax_summary"] = True
    
    result["monthly_tax"] = round(monthly_tax, 2)
    result["annual_tax"] = round(annual_tax, 2)
    
    logger.info(f"[ESCROW-TAX] Monthly tax: ${monthly_tax:,.2f} ({result['calculation_method']})")
    
    return result


# =============================================================================
# MONTHLY INSURANCE CALCULATOR
# =============================================================================

def calculate_monthly_insurance_premiums(loan_id: str) -> Dict[str, Any]:
    """
    Calculate and verify monthly insurance premiums.
    
    Per SOP:
    - Convert yearly premiums to monthly
    - Verify monthly amounts match between forms (Final 1003, Approval, HOI Policy)
    - Validate impound requirements based on loan type and LTV
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with insurance premium calculations:
        {
            "monthly_hoi": float,
            "monthly_flood": float,
            "monthly_mi": float,
            "total_monthly_insurance": float,
            "yearly_hoi": float,
            "yearly_flood": float,
            "sources": dict,
            "warnings": List[str]
        }
    """
    logger.info(f"[ESCROW-INS] Calculating monthly insurance premiums for loan {loan_id}")
    
    result = {
        "monthly_hoi": None,
        "monthly_flood": None,
        "monthly_mi": None,
        "total_monthly_insurance": 0.0,
        "yearly_hoi": None,
        "yearly_flood": None,
        "sources": {},
        "warnings": []
    }
    
    try:
        # Read insurance fields
        field_ids = [
            EscrowFields.MONTHLY_HOI,
            EscrowFields.MONTHLY_FLOOD,
            EscrowFields.MONTHLY_MI,
            EscrowFields.YEARLY_HOI,
            EscrowFields.YEARLY_FLOOD,
        ]
        
        # Filter out None fields
        field_ids = [fid for fid in field_ids if fid is not None]
        
        fields = read_fields(loan_id, field_ids)
        
        # Parse monthly HOI
        monthly_hoi_str = fields.get(EscrowFields.MONTHLY_HOI)
        if monthly_hoi_str:
            result["monthly_hoi"] = _parse_currency(monthly_hoi_str)
            result["sources"]["monthly_hoi"] = f"Field {EscrowFields.MONTHLY_HOI}"
        
        # Parse yearly HOI (can derive monthly if monthly not set)
        if EscrowFields.YEARLY_HOI:
            yearly_hoi_str = fields.get(EscrowFields.YEARLY_HOI)
            if yearly_hoi_str:
                result["yearly_hoi"] = _parse_currency(yearly_hoi_str)
                result["sources"]["yearly_hoi"] = f"Field {EscrowFields.YEARLY_HOI}"
                
                # If monthly not set, calculate from yearly
                if not result["monthly_hoi"] and result["yearly_hoi"]:
                    result["monthly_hoi"] = round(result["yearly_hoi"] / 12, 2)
                    result["sources"]["monthly_hoi"] = f"Calculated from yearly: ${result['yearly_hoi']:,.2f} ÷ 12"
        
        # Parse monthly flood
        monthly_flood_str = fields.get(EscrowFields.MONTHLY_FLOOD)
        if monthly_flood_str:
            result["monthly_flood"] = _parse_currency(monthly_flood_str)
            result["sources"]["monthly_flood"] = f"Field {EscrowFields.MONTHLY_FLOOD}"
        
        # Parse yearly flood (can derive monthly if monthly not set)
        if EscrowFields.YEARLY_FLOOD:
            yearly_flood_str = fields.get(EscrowFields.YEARLY_FLOOD)
            if yearly_flood_str:
                result["yearly_flood"] = _parse_currency(yearly_flood_str)
                result["sources"]["yearly_flood"] = f"Field {EscrowFields.YEARLY_FLOOD}"
                
                # If monthly not set, calculate from yearly
                if not result["monthly_flood"] and result["yearly_flood"]:
                    result["monthly_flood"] = round(result["yearly_flood"] / 12, 2)
                    result["sources"]["monthly_flood"] = f"Calculated from yearly: ${result['yearly_flood']:,.2f} ÷ 12"
        
        # Parse monthly MI
        monthly_mi_str = fields.get(EscrowFields.MONTHLY_MI)
        if monthly_mi_str:
            result["monthly_mi"] = _parse_currency(monthly_mi_str)
            result["sources"]["monthly_mi"] = f"Field {EscrowFields.MONTHLY_MI}"
        
        # Calculate total monthly insurance
        total = 0.0
        if result["monthly_hoi"]:
            total += result["monthly_hoi"]
        if result["monthly_flood"]:
            total += result["monthly_flood"]
        if result["monthly_mi"]:
            total += result["monthly_mi"]
        
        result["total_monthly_insurance"] = round(total, 2)
        
        logger.info(f"[ESCROW-INS] Monthly insurance: HOI=${result['monthly_hoi'] or 0:.2f}, "
                   f"Flood=${result['monthly_flood'] or 0:.2f}, MI=${result['monthly_mi'] or 0:.2f}, "
                   f"Total=${result['total_monthly_insurance']:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"[ESCROW-INS] Error calculating insurance premiums: {e}")
        result["warnings"].append(f"Error: {e}")
        return result


# =============================================================================
# CUSHION MONTHS VALIDATOR
# =============================================================================

def validate_cushion_months(loan_id: str) -> Dict[str, Any]:
    """
    Validate reserve/cushion months are set correctly.
    
    Per SOP Step 19:
    - Tax: 2 months cushion
    - HOI: 2 months cushion
    - Flood: 2 months cushion (if applicable)
    - MI: 0 months cushion (if applicable)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results:
        {
            "tax_cushion": int,
            "hoi_cushion": int,
            "flood_cushion": int,
            "mi_cushion": int,
            "correct_cushions": bool,
            "discrepancies": List[dict],
            "ptf_conditions_added": int
        }
    """
    logger.info(f"[ESCROW-CUSHION] Validating cushion months for loan {loan_id}")
    
    result = {
        "tax_cushion": None,
        "hoi_cushion": None,
        "flood_cushion": None,
        "mi_cushion": None,
        "correct_cushions": True,
        "discrepancies": [],
        "ptf_conditions_added": 0
    }
    
    try:
        # Read cushion/reserve month fields
        field_ids = [
            EscrowFields.TAX_RESERVE_MONTHS,
            EscrowFields.HOI_RESERVE_MONTHS,
            EscrowFields.FLOOD_RESERVE_MONTHS,
            EscrowFields.MI_RESERVE_MONTHS,
        ]
        
        # Filter out None fields
        field_ids = [fid for fid in field_ids if fid is not None]
        
        fields = read_fields(loan_id, field_ids)
        
        # Parse and validate tax cushion
        tax_cushion_str = fields.get(EscrowFields.TAX_RESERVE_MONTHS)
        if tax_cushion_str:
            tax_cushion = int(_parse_currency(tax_cushion_str))
            result["tax_cushion"] = tax_cushion
            
            if tax_cushion != 2:
                result["correct_cushions"] = False
                result["discrepancies"].append({
                    "field": "Tax Reserve Months",
                    "field_id": EscrowFields.TAX_RESERVE_MONTHS,
                    "current": tax_cushion,
                    "expected": 2,
                    "message": f"Tax cushion should be 2 months, found {tax_cushion}"
                })
        
        # Parse and validate HOI cushion
        hoi_cushion_str = fields.get(EscrowFields.HOI_RESERVE_MONTHS)
        if hoi_cushion_str:
            hoi_cushion = int(_parse_currency(hoi_cushion_str))
            result["hoi_cushion"] = hoi_cushion
            
            if hoi_cushion != 2:
                result["correct_cushions"] = False
                result["discrepancies"].append({
                    "field": "HOI Reserve Months",
                    "field_id": EscrowFields.HOI_RESERVE_MONTHS,
                    "current": hoi_cushion,
                    "expected": 2,
                    "message": f"HOI cushion should be 2 months, found {hoi_cushion}"
                })
        
        # Parse and validate Flood cushion (if applicable)
        flood_cushion_str = fields.get(EscrowFields.FLOOD_RESERVE_MONTHS)
        if flood_cushion_str:
            flood_cushion = int(_parse_currency(flood_cushion_str))
            result["flood_cushion"] = flood_cushion
            
            if flood_cushion != 2:
                result["correct_cushions"] = False
                result["discrepancies"].append({
                    "field": "Flood Reserve Months",
                    "field_id": EscrowFields.FLOOD_RESERVE_MONTHS,
                    "current": flood_cushion,
                    "expected": 2,
                    "message": f"Flood cushion should be 2 months, found {flood_cushion}"
                })
        
        # Parse and validate MI cushion (if applicable)
        if EscrowFields.MI_RESERVE_MONTHS:
            mi_cushion_str = fields.get(EscrowFields.MI_RESERVE_MONTHS)
            if mi_cushion_str:
                mi_cushion = int(_parse_currency(mi_cushion_str))
                result["mi_cushion"] = mi_cushion
                
                if mi_cushion != 0:
                    result["correct_cushions"] = False
                    result["discrepancies"].append({
                        "field": "MI Reserve Months",
                        "field_id": EscrowFields.MI_RESERVE_MONTHS,
                        "current": mi_cushion,
                        "expected": 0,
                        "message": f"MI cushion should be 0 months, found {mi_cushion}"
                    })
        
        # Generate PTF conditions for discrepancies
        if result["discrepancies"]:
            for discrepancy in result["discrepancies"]:
                ptf_result = add_ptf_condition(
                    loan_id=loan_id,
                    category="Escrow Setup Error",
                    description=(
                        f"{discrepancy['field']} incorrect: {discrepancy['message']}. "
                        f"Update Aggregate Escrow Account → Setup → Cushion months."
                    ),
                    severity="PTF",
                    assigned_to="Loan Processor"
                )
                
                if ptf_result["success"]:
                    result["ptf_conditions_added"] += 1
        
        logger.info(f"[ESCROW-CUSHION] Cushion months: Tax={result['tax_cushion']}, "
                   f"HOI={result['hoi_cushion']}, Flood={result['flood_cushion']}, MI={result['mi_cushion']}")
        
        if not result["correct_cushions"]:
            logger.warning(f"[ESCROW-CUSHION] Found {len(result['discrepancies'])} cushion errors")
        
        return result
        
    except Exception as e:
        logger.error(f"[ESCROW-CUSHION] Error validating cushion months: {e}")
        return result


# =============================================================================
# IMPOUND REQUIREMENT VALIDATOR
# =============================================================================

def validate_impound_requirements(loan_id: str) -> Dict[str, Any]:
    """
    Validate that impounds are set up correctly based on loan type and LTV.
    
    Per SOP Step 19:
    - FHA: Impounds REQUIRED (taxes + insurance)
    - VA: Impounds REQUIRED (taxes + insurance)
    - USDA: Impounds REQUIRED (taxes + insurance)
    - Conventional >80% LTV: Impounds REQUIRED
    - Conventional ≤80% LTV: Impounds OPTIONAL (except flood - always required)
    - CA Exception: No impounds allowed up to 90% LTV (Conventional only)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results:
        {
            "impounds_required": bool,
            "impounds_set": bool,
            "impound_type": str,
            "correct_setup": bool,
            "rule_applied": str,
            "ptf_condition_added": bool,
            "warnings": List[str]
        }
    """
    logger.info(f"[ESCROW-IMPOUND] Validating impound requirements for loan {loan_id}")
    
    result = {
        "impounds_required": None,
        "impounds_set": None,
        "impound_type": None,
        "correct_setup": None,
        "rule_applied": None,
        "ptf_condition_added": False,
        "warnings": []
    }
    
    try:
        # Read required fields
        field_ids = [
            EscrowFields.LOAN_TYPE,
            EscrowFields.LTV,
            EscrowFields.PROPERTY_STATE,
            EscrowFields.IMPOUND_TYPE,
            EscrowFields.IMPOUNDS_WAIVED,
        ]
        
        # Filter out None fields
        field_ids = [fid for fid in field_ids if fid is not None]
        
        fields = read_fields(loan_id, field_ids)
        
        # Parse loan type
        loan_type = str(fields.get(EscrowFields.LOAN_TYPE, "")).upper()
        ltv_str = fields.get(EscrowFields.LTV)
        ltv = _parse_currency(ltv_str) if ltv_str else None
        state = str(fields.get(EscrowFields.PROPERTY_STATE, "")).upper()
        
        impound_type = fields.get(EscrowFields.IMPOUND_TYPE)
        impounds_waived = fields.get(EscrowFields.IMPOUNDS_WAIVED)
        
        logger.info(f"[ESCROW-IMPOUND] Loan type: {loan_type}, LTV: {ltv}%, State: {state}")
        
        # Determine if impounds required
        impounds_required = False
        rule = None
        
        # FHA/VA/USDA: Always required
        if "FHA" in loan_type or "VA" in loan_type or "USDA" in loan_type:
            impounds_required = True
            rule = f"{loan_type} loans require impounds (taxes + insurance)"
        
        # Conventional with LTV > 80%: Required
        elif "CONV" in loan_type and ltv and ltv > 80:
            # CA Exception: Optional up to 90% LTV
            if state == "CA" and ltv <= 90:
                impounds_required = False
                rule = "CA Conventional: Impounds optional up to 90% LTV"
            else:
                impounds_required = True
                rule = f"Conventional >80% LTV: Impounds required (LTV={ltv}%)"
        
        # Conventional with LTV ≤ 80%: Optional
        elif "CONV" in loan_type and ltv and ltv <= 80:
            impounds_required = False
            rule = f"Conventional ≤80% LTV: Impounds optional (LTV={ltv}%)"
        
        result["impounds_required"] = impounds_required
        result["rule_applied"] = rule
        
        # Check if impounds are set
        impounds_set = (
            impound_type and 
            str(impound_type).lower() not in ["none", "no", "waived", ""] and
            str(impounds_waived).lower() not in ["yes", "y", "true"]
        )
        result["impounds_set"] = impounds_set
        result["impound_type"] = impound_type
        
        # Validate setup
        if impounds_required and not impounds_set:
            result["correct_setup"] = False
            result["warnings"].append(f"Impounds REQUIRED but not set. {rule}")
            
            # Generate PTF condition
            ptf_result = add_ptf_condition(
                loan_id=loan_id,
                category="Impound Setup Error",
                description=(
                    f"Impounds REQUIRED but not set up. {rule}. "
                    f"Request processor to issue COC CD to correct impounds to YES for both taxes and insurance."
                ),
                severity="PTF",
                assigned_to="Loan Processor"
            )
            
            if ptf_result["success"]:
                result["ptf_condition_added"] = True
                logger.warning(f"[ESCROW-IMPOUND] PTF added: Impounds required but not set")
        
        elif not impounds_required and impounds_set:
            result["correct_setup"] = True
            result["warnings"].append(f"Impounds set (optional). {rule}")
        
        else:
            result["correct_setup"] = True
        
        logger.info(f"[ESCROW-IMPOUND] Required: {impounds_required}, Set: {impounds_set}, Correct: {result['correct_setup']}")
        
        # Special note: Flood insurance ALWAYS impounded (even if other impounds waived)
        result["warnings"].append(
            "Note: Flood insurance must be impounded even if general impounds are waived per SOP."
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[ESCROW-IMPOUND] Error validating impound requirements: {e}")
        result["warnings"].append(f"Error: {e}")
        return result


# =============================================================================
# COMBINED ESCROW VALIDATION
# =============================================================================

def validate_escrow_setup(loan_id: str) -> Dict[str, Any]:
    """
    Run complete escrow validation: taxes, insurance, cushions, impounds.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with combined escrow validation results:
        {
            "status": "passed" | "warnings" | "failed",
            "tax_calculation": {...},
            "insurance_premiums": {...},
            "cushion_validation": {...},
            "impound_validation": {...},
            "total_monthly_escrow": float,
            "total_ptf_conditions": int,
            "warnings": List[str],
            "errors": List[str]
        }
    """
    logger.info(f"[ESCROW] Starting complete escrow validation for loan {loan_id}")
    
    # Get loan context first
    try:
        context_fields = [
            EscrowFields.LOAN_TYPE,
            EscrowFields.PROPERTY_STATE,
            EscrowFields.PURCHASE_PRICE,
            EscrowFields.LTV,
            EscrowFields.LOAN_PURPOSE,
        ]
        context_fields = [fid for fid in context_fields if fid is not None]
        context = read_fields(loan_id, context_fields)
        
        state = str(context.get(EscrowFields.PROPERTY_STATE, "")).upper()
        sales_price = _parse_currency(context.get(EscrowFields.PURCHASE_PRICE)) if context.get(EscrowFields.PURCHASE_PRICE) else None
        
        logger.info(f"[ESCROW] Loan context: State={state}, Sales Price=${sales_price:,.2f if sales_price else 0}")
        
    except Exception as e:
        logger.error(f"[ESCROW] Error reading loan context: {e}")
        state = None
        sales_price = None
    
    # Run individual validations
    insurance_premiums = calculate_monthly_insurance_premiums(loan_id)
    cushion_validation = validate_cushion_months(loan_id)
    impound_validation = validate_impound_requirements(loan_id)
    
    # For tax calculation, we need more info (will implement after getting field IDs)
    tax_calculation = {
        "status": "not_implemented",
        "message": "Tax calculation requires additional fields (property type, tax summary). Will implement once field IDs confirmed."
    }
    
    # Calculate total monthly escrow
    total_monthly = 0.0
    if insurance_premiums.get("total_monthly_insurance"):
        total_monthly += insurance_premiums["total_monthly_insurance"]
    
    # Determine overall status
    total_ptf = 0
    total_ptf += cushion_validation.get("ptf_conditions_added", 0)
    total_ptf += impound_validation.get("ptf_condition_added", 0)
    
    warnings = []
    warnings.extend(insurance_premiums.get("warnings", []))
    warnings.extend(cushion_validation.get("discrepancies", []))
    warnings.extend(impound_validation.get("warnings", []))
    
    status = "passed"
    if total_ptf > 0:
        status = "failed"
    elif warnings:
        status = "warnings"
    
    result = {
        "status": status,
        "tax_calculation": tax_calculation,
        "insurance_premiums": insurance_premiums,
        "cushion_validation": cushion_validation,
        "impound_validation": impound_validation,
        "total_monthly_escrow": round(total_monthly, 2),
        "total_ptf_conditions": total_ptf,
        "warnings": warnings,
        "errors": []
    }
    
    logger.info(f"[ESCROW] Validation complete: Status={status}, Total monthly escrow=${total_monthly:.2f}, PTF conditions={total_ptf}")
    
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_currency(value: str) -> float:
    """Parse currency string to float (handles $, commas, %)."""
    if not value:
        return 0.0
    
    # Remove $, commas, spaces, %
    cleaned = str(value).replace("$", "").replace(",", "").replace(" ", "").replace("%", "").strip()
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0




