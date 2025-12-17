"""
HOI (Homeowners Insurance) and Flood Insurance Validation Tools for DrawDocs Verification Agent.

Per SOP Step 2:
- HOI: Verify dwelling coverage ≥ loan amount (with 125% ERC calculation)
- Flood: Verify flood zone, coverage limits ($250k max), policy matches certificate

Generates PTF conditions if:
- HOI dwelling coverage insufficient (HARDSTOP)
- Flood zone mismatch between certificate, appraisal, and policy
- Flood coverage insufficient or exceeds $250k limit
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from agents.drawdocs.tools.primitives import read_fields, add_ptf_condition, log_issue

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR INSURANCE
# =============================================================================

class InsuranceFields:
    """
    Encompass field IDs for insurance validation.
    
    ✅ = Confirmed from master_field_data.csv
    ❌ = Still need to find (see INSURANCE_FIELD_MAPPING.md)
    """
    
    # Loan Amount
    LOAN_AMOUNT = "1109"  # ✅ Confirmed
    
    # HOI (Homeowners Insurance) - CONFIRMED
    HOI_PREMIUM = "642"  # ✅ Fees Hazard Ins Premium Borr
    HOI_MONTHLY = "230"  # ✅ Expenses Proposed Haz Ins (monthly)
    HOI_YEARLY = "HUD42"  # ✅ Hazard Insurance Yearly Premium
    HOI_COMPANY_NAME = "L252"  # ✅ Hazard Insurance Company Name
    HOI_CONTACT = "VEND.X163"  # ✅ Hazard Ins Co Phone
    HOI_AGENT_EMAIL = "VEND.X164"  # ⚠️ Not verified (field exists but not in grep results)
    HOI_RESERVE_MONTHS = "1387"  # ✅ Fees Hazard Ins # of Mos Reserve Required
    
    # HOI - NEWLY FOUND! ✅
    HOI_DWELLING_AMOUNT = "VEND.X445"  # ✅ Coverage Amount (from Quick Entry popup)
    HOI_POLICY_EXPIRATION = "VEND.X444"  # ✅ Renewal Date (from Quick Entry popup)
    
    # HOI - STILL MISSING (will use defaults/skip)
    HOI_ERC_PERCENT = None  # ❌ Extended Replacement Cost % (will default to 125%)
    HOI_LOSS_PAYEE = None  # ❌ Loss Payee / Mortgagee Clause (will skip validation)
    
    # Flood Insurance - CONFIRMED
    FLOOD_PREMIUM = "643"  # ✅ Fees Flood Ins Premium Borr
    FLOOD_MONTHLY = "235"  # ✅ Fees Flood Ins Per Mo
    FLOOD_YEARLY = "HUD44"  # ✅ Flood Insurance Yearly Premium
    FLOOD_COMPANY_NAME = "1500"  # ✅ Flood Insurance Company Name
    FLOOD_CONTACT = "VEND.X13"  # ✅ Flood Ins Co Contact
    FLOOD_RESERVE_MONTHS = "1388"  # ✅ Fees Flood Ins # of Mos Reserve Required
    
    # Flood - COMPLETE! ✅✅✅
    FLOOD_ZONE = "541"  # ✅ Flood Zone from Property Information form (A, V, X, etc.)
    FLOOD_COVERAGE_AMOUNT = "VEND.X446"  # ✅ Coverage Amount (from Quick Entry popup)
    FLOOD_POLICY_NUMBER = "VEND.X22"  # ✅ Policy Number (from Property Information)
    FLOOD_POLICY_EXPIRATION = "VEND.X448"  # ✅ Renewal Date (from Quick Entry popup)
    FLOOD_DETERMINATION_NUMBER = "2364"  # ✅ Determination # / NFIP Community # (from Property Information)
    
    # Appraisal (for estimated cost comparison)
    APPRAISED_VALUE = "356"  # ✅ Confirmed
    
    # Property State (for state-specific rules)
    PROPERTY_STATE = "14"  # ✅ Confirmed


# =============================================================================
# HOI VALIDATION
# =============================================================================

def validate_hoi_coverage(loan_id: str) -> Dict[str, Any]:
    """
    Validate Homeowners Insurance (HOI) dwelling coverage.
    
    Per SOP Step 2:
    1. Calculate total coverage: Dwelling Amount × (1 + ERC%)
    2. Verify total coverage ≥ loan amount
    3. If insufficient: HARDSTOP - add PTF condition
    4. If dwelling inadequate but estimated cost from appraisal covers: OK
    5. Verify borrower name, property address, loss payee on master policy
    6. Check renewal date (within 2 months of first payment = collect renewal premium)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results:
        {
            "status": "passed" | "insufficient" | "needs_appraisal_check" | "error",
            "loan_amount": float,
            "dwelling_amount": float,
            "erc_percent": float (e.g., 1.25 for 125%),
            "total_coverage": float,
            "coverage_sufficient": bool,
            "ptf_condition_added": bool,
            "ptf_condition_id": Optional[str],
            "warnings": List[str],
            "error": Optional[str]
        }
    """
    logger.info(f"[HOI] Starting HOI coverage validation for loan {loan_id}")
    
    result = {
        "status": "unknown",
        "loan_amount": None,
        "dwelling_amount": None,
        "erc_percent": None,
        "total_coverage": None,
        "coverage_sufficient": None,
        "ptf_condition_added": False,
        "ptf_condition_id": None,
        "warnings": [],
        "error": None
    }
    
    try:
        # Read required fields (filter out None values)
        field_ids = [
            InsuranceFields.LOAN_AMOUNT,
            InsuranceFields.HOI_DWELLING_AMOUNT,
            InsuranceFields.HOI_ERC_PERCENT,
            InsuranceFields.APPRAISED_VALUE,
            InsuranceFields.HOI_POLICY_EXPIRATION,
            InsuranceFields.HOI_LOSS_PAYEE,
            InsuranceFields.HOI_COMPANY_NAME,
        ]
        
        # Filter out None field IDs (fields not yet mapped)
        field_ids = [fid for fid in field_ids if fid is not None]
        
        fields = read_fields(loan_id, field_ids)
        
        # Parse loan amount
        loan_amount_str = fields.get(InsuranceFields.LOAN_AMOUNT)
        if not loan_amount_str:
            error_msg = "Loan amount not found in Encompass"
            logger.error(f"[HOI] {error_msg}")
            result["status"] = "error"
            result["error"] = error_msg
            return result
        
        loan_amount = _parse_currency(loan_amount_str)
        result["loan_amount"] = loan_amount
        logger.info(f"[HOI] Loan amount: ${loan_amount:,.2f}")
        
        # Check if dwelling amount field is mapped
        if InsuranceFields.HOI_DWELLING_AMOUNT is None:
            warning = (
                "HOI dwelling amount field not yet mapped in Encompass - cannot validate coverage. "
                "See INSURANCE_FIELD_MAPPING.md for instructions on finding this field ID."
            )
            logger.warning(f"[HOI] {warning}")
            result["status"] = "field_not_mapped"
            result["error"] = warning
            result["warnings"].append(warning)
            return result
        
        # Parse dwelling amount
        dwelling_str = fields.get(InsuranceFields.HOI_DWELLING_AMOUNT)
        if not dwelling_str:
            warning = "HOI dwelling amount is empty in Encompass"
            logger.warning(f"[HOI] {warning}")
            result["status"] = "data_missing"
            result["error"] = warning
            result["warnings"].append(warning)
            return result
        
        dwelling_amount = _parse_currency(dwelling_str)
        result["dwelling_amount"] = dwelling_amount
        logger.info(f"[HOI] Dwelling amount: ${dwelling_amount:,.2f}")
        
        # Parse ERC percentage (default to 125% if not found)
        if InsuranceFields.HOI_ERC_PERCENT is not None:
            erc_str = fields.get(InsuranceFields.HOI_ERC_PERCENT)
            if erc_str:
                erc_percent = _parse_percent(erc_str) / 100  # Convert 125 to 1.25
                logger.info(f"[HOI] ERC%: {erc_percent * 100:.1f}%")
            else:
                erc_percent = 0.25  # Default 25% ERC (so total = 1 + 0.25 = 1.25)
                logger.info(f"[HOI] ERC% field is empty, using default 25% (125% total coverage)")
        else:
            erc_percent = 0.25  # Default 25% ERC (so total = 1 + 0.25 = 1.25)
            logger.info(f"[HOI] ERC% field not mapped, using default 25% (125% total coverage)")
        
        result["erc_percent"] = erc_percent
        
        # Calculate total coverage: Dwelling × (1 + ERC%)
        total_coverage = dwelling_amount * (1 + erc_percent)
        result["total_coverage"] = total_coverage
        logger.info(f"[HOI] Total coverage: Dwelling ${dwelling_amount:,.2f} × {(1 + erc_percent):.2%} = ${total_coverage:,.2f}")
        
        # Check if coverage sufficient
        coverage_sufficient = total_coverage >= loan_amount
        result["coverage_sufficient"] = coverage_sufficient
        
        if coverage_sufficient:
            result["status"] = "passed"
            logger.info(f"[HOI] ✓ Coverage sufficient: ${total_coverage:,.2f} ≥ ${loan_amount:,.2f}")
        else:
            # Coverage insufficient - check appraisal estimated cost as fallback
            logger.warning(f"[HOI] ⚠ Coverage insufficient: ${total_coverage:,.2f} < ${loan_amount:,.2f}")
            
            appraised_value_str = fields.get(InsuranceFields.APPRAISED_VALUE)
            if appraised_value_str:
                appraised_value = _parse_currency(appraised_value_str)
                logger.info(f"[HOI] Checking appraisal estimated cost: ${appraised_value:,.2f}")
                
                # Per SOP: If coverage not enough but appraisal estimated cost covers loan amount, OK
                if total_coverage >= appraised_value * 0.8:  # Use 80% of appraised value as estimated cost
                    result["status"] = "needs_appraisal_check"
                    result["warnings"].append(
                        f"HOI coverage ${total_coverage:,.2f} is less than loan amount ${loan_amount:,.2f}, "
                        f"but may be sufficient per appraisal estimated cost. Manual review required."
                    )
                    logger.info(f"[HOI] Coverage may be sufficient per appraisal - manual review needed")
                else:
                    # HARDSTOP: Insufficient coverage
                    result["status"] = "insufficient"
                    ptf_result = add_ptf_condition(
                        loan_id=loan_id,
                        category="HOI Insufficient Coverage",
                        description=(
                            f"HARDSTOP - Insufficient HOI dwelling coverage. "
                            f"Total coverage ${total_coverage:,.2f} is less than loan amount ${loan_amount:,.2f}. "
                            f"Reach out to processor for updated HOI with sufficient coverage."
                        ),
                        severity="PTF",
                        assigned_to="Loan Processor"
                    )
                    
                    if ptf_result["success"]:
                        result["ptf_condition_added"] = True
                        result["ptf_condition_id"] = ptf_result.get("condition_id")
                        logger.info(f"[HOI] PTF condition added: {ptf_result.get('condition_id')}")
            else:
                # No appraisal value - just flag as insufficient
                result["status"] = "insufficient"
                ptf_result = add_ptf_condition(
                    loan_id=loan_id,
                    category="HOI Insufficient Coverage",
                    description=(
                        f"HARDSTOP - Insufficient HOI dwelling coverage. "
                        f"Total coverage ${total_coverage:,.2f} is less than loan amount ${loan_amount:,.2f}. "
                        f"Reach out to processor for updated HOI with sufficient coverage."
                    ),
                    severity="PTF",
                    assigned_to="Loan Processor"
                )
                
                if ptf_result["success"]:
                    result["ptf_condition_added"] = True
                    result["ptf_condition_id"] = ptf_result.get("condition_id")
        
        # Additional checks: Loss payee, expiration date
        if InsuranceFields.HOI_LOSS_PAYEE is not None:
            loss_payee = fields.get(InsuranceFields.HOI_LOSS_PAYEE)
            if loss_payee:
                if "ALL WESTERN MORTGAGE" not in loss_payee.upper():
                    result["warnings"].append(
                        f"Loss payee/mortgagee clause may not have correct lender name. Found: '{loss_payee}'. "
                        f"Expected: 'ALL WESTERN MORTGAGE, INC.'"
                    )
        else:
            result["warnings"].append("HOI Loss Payee field not yet mapped - cannot verify mortgagee clause")
        
        return result
        
    except Exception as e:
        logger.error(f"[HOI] Error validating HOI coverage: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


# =============================================================================
# FLOOD VALIDATION
# =============================================================================

def validate_flood_insurance(loan_id: str) -> Dict[str, Any]:
    """
    Validate Flood Insurance (if property in flood zone).
    
    Per SOP Step 2:
    1. Check if property in flood zone (A, V)
    2. If yes, verify flood insurance required
    3. Check coverage limits:
       - Max allowable: $250k
       - If loan > $250k: Coverage = $250k
       - If loan < $250k: Coverage ≥ loan amount
    4. Verify flood zone and NFIP map # match between certificate, appraisal, and policy
    5. If mismatch: Add PTF condition to correct
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results:
        {
            "status": "not_required" | "passed" | "insufficient" | "mismatch" | "error",
            "property_in_flood_zone": bool,
            "flood_zone": Optional[str],
            "loan_amount": float,
            "coverage_amount": Optional[float],
            "coverage_sufficient": bool,
            "max_coverage": float (250000.00),
            "nfip_map_matches": bool,
            "ptf_conditions_added": int,
            "warnings": List[str],
            "error": Optional[str]
        }
    """
    logger.info(f"[FLOOD] Starting flood insurance validation for loan {loan_id}")
    
    result = {
        "status": "unknown",
        "property_in_flood_zone": False,
        "flood_zone": None,
        "loan_amount": None,
        "coverage_amount": None,
        "coverage_sufficient": None,
        "max_coverage": 250000.00,
        "nfip_map_matches": None,
        "ptf_conditions_added": 0,
        "warnings": [],
        "error": None
    }
    
    try:
        # Read required fields (filter out None values)
        field_ids = [
            InsuranceFields.LOAN_AMOUNT,
            InsuranceFields.FLOOD_ZONE,
            InsuranceFields.FLOOD_COVERAGE_AMOUNT,
            InsuranceFields.FLOOD_DETERMINATION_NUMBER,
        ]
        
        # Filter out None field IDs (fields not yet mapped)
        field_ids = [fid for fid in field_ids if fid is not None]
        
        fields = read_fields(loan_id, field_ids)
        
        # Parse loan amount
        loan_amount_str = fields.get(InsuranceFields.LOAN_AMOUNT)
        if not loan_amount_str:
            error_msg = "Loan amount not found in Encompass"
            logger.error(f"[FLOOD] {error_msg}")
            result["status"] = "error"
            result["error"] = error_msg
            return result
        
        loan_amount = _parse_currency(loan_amount_str)
        result["loan_amount"] = loan_amount
        logger.info(f"[FLOOD] Loan amount: ${loan_amount:,.2f}")
        
        # Check if flood zone field is mapped
        if InsuranceFields.FLOOD_ZONE is None:
            warning = (
                "Flood zone field not yet mapped in Encompass - cannot validate flood insurance. "
                "See INSURANCE_FIELD_MAPPING.md for instructions on finding this field ID."
            )
            logger.warning(f"[FLOOD] {warning}")
            result["status"] = "field_not_mapped"
            result["error"] = warning
            result["warnings"].append(warning)
            return result
        
        # Check flood zone
        flood_zone_str = fields.get(InsuranceFields.FLOOD_ZONE)
        if not flood_zone_str:
            warning = "Flood zone is empty in Encompass - cannot determine if flood insurance required"
            logger.warning(f"[FLOOD] {warning}")
            result["status"] = "data_missing"
            result["error"] = warning
            result["warnings"].append(warning)
            return result
        
        flood_zone = flood_zone_str.strip().upper()
        result["flood_zone"] = flood_zone
        logger.info(f"[FLOOD] Flood zone: {flood_zone}")
        
        # Check if property in flood zone (A or V)
        property_in_flood_zone = flood_zone in ["A", "V"] or flood_zone.startswith("A") or flood_zone.startswith("V")
        result["property_in_flood_zone"] = property_in_flood_zone
        
        if not property_in_flood_zone:
            result["status"] = "not_required"
            logger.info(f"[FLOOD] ✓ Property not in flood zone (Zone: {flood_zone}) - flood insurance not required")
            return result
        
        logger.info(f"[FLOOD] Property IS in flood zone - validating flood insurance...")
        
        # Check if flood coverage amount field is mapped
        if InsuranceFields.FLOOD_COVERAGE_AMOUNT is None:
            warning = (
                f"Property is in flood zone {flood_zone}, but flood coverage amount field not yet mapped. "
                "Cannot validate flood insurance coverage. See INSURANCE_FIELD_MAPPING.md."
            )
            logger.warning(f"[FLOOD] {warning}")
            result["status"] = "field_not_mapped"
            result["error"] = warning
            result["warnings"].append(warning)
            return result
        
        # Parse flood coverage amount
        coverage_str = fields.get(InsuranceFields.FLOOD_COVERAGE_AMOUNT)
        if not coverage_str:
            # No flood insurance found - add PTF
            result["status"] = "insufficient"
            logger.warning(f"[FLOOD] No flood coverage amount found - insurance missing or not recorded")
            
            ptf_result = add_ptf_condition(
                loan_id=loan_id,
                category="Flood Insurance Required",
                description=(
                    f"Property is in flood zone {flood_zone}. Flood insurance required. "
                    f"Reach out to processor for flood insurance policy."
                ),
                severity="PTF",
                assigned_to="Loan Processor"
            )
            
            if ptf_result["success"]:
                result["ptf_conditions_added"] += 1
                logger.info(f"[FLOOD] PTF condition added for missing flood insurance")
            
            return result
        
        coverage_amount = _parse_currency(coverage_str)
        result["coverage_amount"] = coverage_amount
        logger.info(f"[FLOOD] Flood coverage: ${coverage_amount:,.2f}")
        
        # Validate coverage amount
        # Max allowable: $250k
        max_coverage = 250000.00
        
        if loan_amount > max_coverage:
            # Loan > $250k: Coverage should be $250k
            required_coverage = max_coverage
        else:
            # Loan ≤ $250k: Coverage should be at least loan amount
            required_coverage = loan_amount
        
        coverage_sufficient = coverage_amount >= required_coverage
        result["coverage_sufficient"] = coverage_sufficient
        
        if coverage_sufficient:
            result["status"] = "passed"
            logger.info(f"[FLOOD] ✓ Coverage sufficient: ${coverage_amount:,.2f} ≥ ${required_coverage:,.2f}")
        else:
            result["status"] = "insufficient"
            logger.warning(f"[FLOOD] ⚠ Coverage insufficient: ${coverage_amount:,.2f} < ${required_coverage:,.2f}")
            
            ptf_result = add_ptf_condition(
                loan_id=loan_id,
                category="Flood Insurance Insufficient",
                description=(
                    f"Flood insurance coverage ${coverage_amount:,.2f} is less than required ${required_coverage:,.2f}. "
                    f"Reach out to processor for updated flood insurance with sufficient coverage."
                ),
                severity="PTF",
                assigned_to="Loan Processor"
            )
            
            if ptf_result["success"]:
                result["ptf_conditions_added"] += 1
        
        # Check if coverage exceeds $250k max
        if coverage_amount > max_coverage:
            result["warnings"].append(
                f"Flood insurance coverage ${coverage_amount:,.2f} exceeds maximum allowable $250,000. "
                f"Verify with processor."
            )
        
        # TODO: Add NFIP map number validation (compare certificate vs appraisal vs policy)
        # This would require reading flood certificate and appraisal flood zone fields
        
        return result
        
    except Exception as e:
        logger.error(f"[FLOOD] Error validating flood insurance: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_currency(value: str) -> float:
    """Parse currency string to float (handles $, commas)."""
    if not value:
        return 0.0
    
    # Remove $, commas, spaces
    cleaned = str(value).replace("$", "").replace(",", "").replace(" ", "").strip()
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_percent(value: str) -> float:
    """Parse percentage string to float (handles %)."""
    if not value:
        return 0.0
    
    # Remove %, spaces
    cleaned = str(value).replace("%", "").replace(" ", "").strip()
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# =============================================================================
# COMBINED VALIDATION
# =============================================================================

def validate_insurance(loan_id: str) -> Dict[str, Any]:
    """
    Run both HOI and Flood insurance validation.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with combined results:
        {
            "status": "success" | "failed" | "warnings",
            "hoi_validation": {...},
            "flood_validation": {...},
            "total_ptf_conditions": int,
            "hardstops": List[str]
        }
    """
    logger.info(f"[INSURANCE] Starting full insurance validation for loan {loan_id}")
    
    # Run HOI validation
    hoi_result = validate_hoi_coverage(loan_id)
    
    # Run Flood validation
    flood_result = validate_flood_insurance(loan_id)
    
    # Combine results
    total_ptf = 0
    if hoi_result.get("ptf_condition_added"):
        total_ptf += 1
    total_ptf += flood_result.get("ptf_conditions_added", 0)
    
    hardstops = []
    if hoi_result.get("status") == "insufficient":
        hardstops.append("HOI coverage insufficient - HARDSTOP")
    if flood_result.get("status") == "insufficient":
        hardstops.append("Flood insurance insufficient or missing")
    
    overall_status = "success"
    if hardstops:
        overall_status = "failed"
    elif hoi_result.get("warnings") or flood_result.get("warnings"):
        overall_status = "warnings"
    
    result = {
        "status": overall_status,
        "hoi_validation": hoi_result,
        "flood_validation": flood_result,
        "total_ptf_conditions": total_ptf,
        "hardstops": hardstops
    }
    
    logger.info(f"[INSURANCE] Validation complete: {overall_status}, PTF conditions: {total_ptf}")
    
    return result

