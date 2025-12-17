"""Form validation tools for GAPS implementation.

Implements validation for gaps identified in GAPS.md:
- G2: FACT Act checkboxes
- G10: URLA Part 1 validations
- G11: LO NMLS info validation
- G12: Borrower Summary validations
- G13: Comments/Notes review
- G14: Credit validation by purpose
- G15: Consent 60-day validation
- G17: Company license check
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.encompass_io import read_fields

logger = logging.getLogger(__name__)


@tool
def validate_fact_act_checkboxes(loan_id: str) -> dict:
    """Validate FACT Act checkboxes are marked (G2 - CRITICAL).
    
    Per GAPS.md Lines 158-162:
    - Check if "Transaction" checkbox is marked
    - Check if "Settlement Service" checkbox is marked
    
    UNKNOWN field IDs - logs warning for manual verification.
    Related fields we DO have: 4174 (FACT Act date), DISCLOSURE.X637
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[G2] Validating FACT Act checkboxes for loan {loan_id[:8]}...")
    logger.warning("[G2] FACT Act checkbox field IDs not mapped - requires manual verification in Encompass")
    
    try:
        # Read related fields we DO have
        fields_to_check = ["4174", "DISCLOSURE.X637"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION-G2]")
        
        result = {
            "gap_id": "G2",
            "gap_name": "FACT Act Checkboxes",
            "status": "partial_check",
            "related_fields_checked": {
                "fact_act_date": loan_data.get("4174"),
                "disclosure_x637": loan_data.get("DISCLOSURE.X637"),
            },
            "warnings": [
                "FACT Act 'Transaction' checkbox field ID UNKNOWN - manual verification required",
                "FACT Act 'Settlement Service' checkbox field ID UNKNOWN - manual verification required"
            ],
            "requires_manual_verification": True,
        }
        
        logger.info(f"[G2] Partial validation complete - manual verification needed")
        return result
        
    except Exception as e:
        logger.error(f"[G2] Error validating FACT Act: {e}")
        return {
            "gap_id": "G2",
            "status": "error",
            "error": str(e),
            "requires_manual_verification": True,
        }


@tool
def validate_urla_part1(loan_id: str) -> dict:
    """Validate 1003 URLA Part 1 fields (G10).
    
    Per GAPS.md Lines 184-189:
    - Citizenship (UNKNOWN)
    - Marital Status (52)
    - Mailing Same as Current (1819)
    - Military Service (URLA.X13)
    - Language Preference (URLA.X21)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[G10] Validating URLA Part 1 fields for loan {loan_id[:8]}...")
    logger.warning("[G10] Citizenship field ID UNKNOWN - requires manual verification in Encompass")
    
    try:
        # Fields we can check
        fields_to_check = ["52", "1819", "URLA.X13", "URLA.X21"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION]")
        
        missing_fields = []
        valid_fields = []
        
        # Check Marital Status (52)
        if not loan_data.get("52"):
            missing_fields.append("Marital Status (52)")
        else:
            valid_fields.append("Marital Status (52)")
        
        # Check Mailing Same as Current (1819)
        if loan_data.get("1819") is None:
            missing_fields.append("Mailing Same as Current (1819)")
        else:
            valid_fields.append("Mailing Same as Current (1819)")
        
        # Check Military Service (URLA.X13)
        if not loan_data.get("URLA.X13"):
            missing_fields.append("Military Service (URLA.X13)")
        else:
            valid_fields.append("Military Service (URLA.X13)")
        
        # Check Language Preference (URLA.X21)
        if not loan_data.get("URLA.X21"):
            missing_fields.append("Language Preference (URLA.X21)")
        else:
            valid_fields.append("Language Preference (URLA.X21)")
        
        all_valid = len(missing_fields) == 0
        
        result = {
            "gap_id": "G10",
            "gap_name": "URLA Part 1 Validations",
            "status": "checked" if all_valid else "incomplete",
            "fields_checked": len(fields_to_check),
            "valid_fields": valid_fields,
            "missing_fields": missing_fields,
            "all_valid": all_valid,
            "warnings": [
                "Citizenship field ID UNKNOWN - manual verification required"
            ],
            "requires_manual_verification": True,
        }
        
        if missing_fields:
            logger.warning(f"[G10] Missing fields: {missing_fields}")
        else:
            logger.info(f"[G10] All known fields valid")
        
        return result
        
    except Exception as e:
        logger.error(f"[G10] Error validating URLA Part 1: {e}")
        return {
            "gap_id": "G10",
            "status": "error",
            "error": str(e),
        }


@tool
def validate_lo_nmls_info(loan_id: str) -> dict:
    """Validate LO NMLS = 14210 and Section 5 Declarations (G11).
    
    Per GAPS.md Lines 190-194:
    - Verify LO NMLS ID is 14210
    - Validate Section 5 Declarations (Part 4)
    
    External NMLS Consumer Access API - not implemented, logs TODO.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with LO validation results
    """
    logger.info(f"[G11] Validating LO NMLS info for loan {loan_id[:8]}...")
    logger.info("[G11] External NMLS Consumer Access API not implemented - add if needed")
    
    try:
        # Check LO NMLS field (assuming common field IDs)
        # Common LO fields: 317 (LO Name), 359 (LO NMLS), 4000 (LO License)
        fields_to_check = ["317", "359", "4000"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION]")
        
        lo_nmls = loan_data.get("359")
        lo_name = loan_data.get("317")
        
        result = {
            "gap_id": "G11",
            "gap_name": "LO NMLS Info Validation",
            "lo_name": lo_name,
            "lo_nmls_id": lo_nmls,
            "expected_nmls": "14210",
            "nmls_matches": str(lo_nmls) == "14210" if lo_nmls else False,
            "status": "checked",
            "warnings": [],
        }
        
        if not lo_nmls:
            result["warnings"].append("LO NMLS ID not found - field 359 may be incorrect")
            logger.warning(f"[G11] LO NMLS ID not found")
        elif str(lo_nmls) != "14210":
            result["warnings"].append(f"LO NMLS ID {lo_nmls} does not match expected 14210")
            logger.warning(f"[G11] LO NMLS mismatch: {lo_nmls} != 14210")
        else:
            logger.info(f"[G11] LO NMLS validated: {lo_nmls}")
        
        result["info"] = "NMLS Consumer Access API integration pending for full validation"
        
        return result
        
    except Exception as e:
        logger.error(f"[G11] Error validating LO NMLS: {e}")
        return {
            "gap_id": "G11",
            "status": "error",
            "error": str(e),
        }


@tool
def validate_borrower_summary(loan_id: str) -> dict:
    """Validate Borrower Summary section (G12).
    
    Per GAPS.md Lines 195-204:
    - Channel = Bank (2626)
    - Status = Active (1393)
    - Vesting = Individual (4008)
    - Consent validity days (UNKNOWN)
    - Company's Agent = CoreLogic (UNKNOWN)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[G12] Validating Borrower Summary for loan {loan_id[:8]}...")
    logger.warning("[G12] Consent validity days field ID UNKNOWN - requires manual verification")
    logger.warning("[G12] CoreLogic agent info field ID UNKNOWN - requires manual verification")
    
    try:
        fields_to_check = ["2626", "1393", "4008"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION]")
        
        channel = loan_data.get("2626")
        status = loan_data.get("1393")
        vesting = loan_data.get("4008")
        
        validations = {
            "channel_is_bank": channel == "Bank" if channel else None,
            "status_is_active": status == "Active" if status else None,
            "vesting_is_individual": vesting == "Individual" if vesting else None,
        }
        
        warnings = []
        if channel != "Bank":
            warnings.append(f"Channel is '{channel}', expected 'Bank'")
        if status != "Active":
            warnings.append(f"Status is '{status}', expected 'Active'")
        if vesting != "Individual":
            warnings.append(f"Vesting is '{vesting}', expected 'Individual'")
        
        # Add warnings for unknown fields
        warnings.extend([
            "Consent validity days field ID UNKNOWN - manual verification required",
            "CoreLogic agent info field ID UNKNOWN - manual verification required"
        ])
        
        result = {
            "gap_id": "G12",
            "gap_name": "Borrower Summary Validations",
            "status": "checked",
            "fields": {
                "channel": channel,
                "status": status,
                "vesting": vesting,
            },
            "validations": validations,
            "all_valid": all(v for v in validations.values() if v is not None),
            "warnings": warnings,
            "requires_manual_verification": True,
        }
        
        if warnings:
            logger.warning(f"[G12] Validation warnings: {warnings}")
        else:
            logger.info(f"[G12] All known validations passed")
        
        return result
        
    except Exception as e:
        logger.error(f"[G12] Error validating Borrower Summary: {e}")
        return {
            "gap_id": "G12",
            "status": "error",
            "error": str(e),
        }


@tool
def check_disclosure_comments(loan_id: str) -> dict:
    """Read Comments/Notes section for special instructions (G13).
    
    Per GAPS.md Lines 205-206:
    - Review Comments/Notes for special instructions
    
    Field ID UNKNOWN - logs that manual review needed.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with comments check results
    """
    logger.info(f"[G13] Checking disclosure comments for loan {loan_id[:8]}...")
    logger.warning("[G13] Comments/Notes field ID UNKNOWN - requires manual review in Encompass")
    
    return {
        "gap_id": "G13",
        "gap_name": "Comments/Notes Review",
        "status": "manual_review_required",
        "message": "Please manually review Comments/Notes section in Encompass for special instructions",
        "warnings": [
            "Comments/Notes field ID UNKNOWN - manual review required"
        ],
        "requires_manual_verification": True,
    }


@tool
def validate_credit_by_purpose(loan_id: str) -> dict:
    """Validate lender/seller credits by loan purpose (G14).
    
    Per GAPS.md Lines 207-210:
    - For Purchase: Validate seller credit (4795)
    - For Refi: Validate lender credit (4794)
    - Check loan purpose (HMDA.X80)
    - Check CD Total Lender Credit (CD2.XSTLC)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with credit validation results
    """
    logger.info(f"[G14] Validating credits by purpose for loan {loan_id[:8]}...")
    
    try:
        fields_to_check = ["HMDA.X80", "CD2.XSTLC", "4794", "4795"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION]")
        
        loan_purpose = loan_data.get("HMDA.X80")
        cd_total_lender_credit = loan_data.get("CD2.XSTLC")
        lender_credit = loan_data.get("4794")
        seller_credit = loan_data.get("4795")
        
        warnings = []
        validations = {}
        
        if loan_purpose == "Purchase":
            validations["purpose"] = "Purchase"
            validations["checking"] = "seller_credit"
            if seller_credit:
                validations["seller_credit_present"] = True
                logger.info(f"[G14] Purchase loan - Seller credit: ${seller_credit}")
            else:
                validations["seller_credit_present"] = False
                warnings.append("Purchase loan but no seller credit found (4795)")
        
        elif loan_purpose in ["Refinance", "NoCash-Out Refinance", "Cash-Out Refinance"]:
            validations["purpose"] = loan_purpose
            validations["checking"] = "lender_credit"
            if lender_credit:
                validations["lender_credit_present"] = True
                logger.info(f"[G14] Refi loan - Lender credit: ${lender_credit}")
            else:
                validations["lender_credit_present"] = False
                warnings.append(f"{loan_purpose} loan but no lender credit found (4794)")
        else:
            warnings.append(f"Unknown loan purpose: {loan_purpose}")
        
        result = {
            "gap_id": "G14",
            "gap_name": "Credit Validation by Purpose",
            "status": "checked",
            "loan_purpose": loan_purpose,
            "lender_credit": lender_credit,
            "seller_credit": seller_credit,
            "cd_total_lender_credit": cd_total_lender_credit,
            "validations": validations,
            "warnings": warnings,
        }
        
        if warnings:
            logger.warning(f"[G14] Validation warnings: {warnings}")
        else:
            logger.info(f"[G14] Credit validation passed")
        
        return result
        
    except Exception as e:
        logger.error(f"[G14] Error validating credits: {e}")
        return {
            "gap_id": "G14",
            "status": "error",
            "error": str(e),
        }


@tool
def validate_consent_validity(loan_id: str) -> dict:
    """Validate eConsent within 60 days and reason not blank (G15).
    
    Per GAPS.md Lines 211-213:
    - eConsent date within 60 days (3983)
    - eConsent reason not blank (UNKNOWN)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with consent validation results
    """
    logger.info(f"[G15] Validating eConsent validity for loan {loan_id[:8]}...")
    logger.warning("[G15] eConsent reason field ID UNKNOWN - requires manual verification")
    
    try:
        fields_to_check = ["3983"]
        loan_data = read_fields(loan_id, fields_to_check, context="[VERIFICATION]")
        
        econsent_date_str = loan_data.get("3983")
        
        warnings = []
        validations = {}
        
        if econsent_date_str:
            try:
                # Parse date (assuming format YYYY-MM-DD or MM/DD/YYYY)
                if "/" in econsent_date_str:
                    econsent_date = datetime.strptime(econsent_date_str, "%m/%d/%Y")
                else:
                    econsent_date = datetime.strptime(econsent_date_str, "%Y-%m-%d")
                
                today = datetime.now()
                days_ago = (today - econsent_date).days
                
                validations["econsent_date"] = econsent_date_str
                validations["days_ago"] = days_ago
                validations["within_60_days"] = days_ago <= 60
                
                if days_ago > 60:
                    warnings.append(f"eConsent date is {days_ago} days old (> 60 days)")
                    logger.warning(f"[G15] eConsent expired: {days_ago} days old")
                else:
                    logger.info(f"[G15] eConsent valid: {days_ago} days old")
            
            except Exception as e:
                warnings.append(f"Could not parse eConsent date: {econsent_date_str}")
                logger.error(f"[G15] Date parse error: {e}")
        else:
            warnings.append("eConsent date not found (3983)")
            logger.warning(f"[G15] eConsent date missing")
        
        # Add warning for unknown field
        warnings.append("eConsent reason field ID UNKNOWN - manual verification required")
        
        result = {
            "gap_id": "G15",
            "gap_name": "Consent 60-Day Validation",
            "status": "checked",
            "validations": validations,
            "warnings": warnings,
            "requires_manual_verification": True,
        }
        
        return result
        
    except Exception as e:
        logger.error(f"[G15] Error validating consent: {e}")
        return {
            "gap_id": "G15",
            "status": "error",
            "error": str(e),
        }


@tool
def validate_company_license(loan_id: str) -> dict:
    """Validate Company License #204 is present (G17).
    
    Per GAPS.md Lines 216-217:
    - Check Company License field = 204
    
    Field ID UNKNOWN - logs warning for manual verification.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with license validation results
    """
    logger.info(f"[G17] Validating Company License for loan {loan_id[:8]}...")
    logger.warning("[G17] Company License field ID UNKNOWN - requires manual verification in Encompass")
    
    return {
        "gap_id": "G17",
        "gap_name": "Company License Check",
        "status": "manual_verification_required",
        "expected_value": "204",
        "message": "Please manually verify Company License = 204 in Encompass",
        "warnings": [
            "Company License field ID UNKNOWN - manual verification required"
        ],
        "requires_manual_verification": True,
    }


@tool
def verify_usps_address(loan_id: str) -> dict:
    """Validate subject property address via USPS API (G9).
    
    Per GAPS.md Lines 180-183:
    - Validate subject property address using USPS Address API v3
    - Standardize address format
    - Verify deliverability
    
    Returns {"success": False, "error": "Client credentials not set"} if credentials missing.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with USPS validation results
    """
    logger.info(f"[G9] Validating USPS address for loan {loan_id[:8]}...")
    
    try:
        from packages.shared.usps_validator import USPSAddressValidator, validate_address_sync
        
        # Get subject property address from loan
        # Subject property address fields
        # Common fields: 11 (street), 12 (city), 14 (state), 15 (ZIP)
        address_fields = ["11", "12", "14", "15"]
        loan_data = read_fields(loan_id, address_fields, context="[VERIFICATION-G9]")
        
        street_address = loan_data.get("11")
        city = loan_data.get("12")
        state = loan_data.get("14")
        zip_code = loan_data.get("15")
        
        if not street_address:
            logger.warning("[G9] No street address found in loan")
            return {
                "gap_id": "G9",
                "gap_name": "USPS Address Validation",
                "status": "error",
                "error": "No street address found in loan (field 11)"
            }
        
        # Validate with USPS
        logger.info(f"[G9] Validating address: {street_address}, {city}, {state} {zip_code}")
        
        result = validate_address_sync(
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code
        )
        
        if not result.success:
            if result.error == "USPS credentials not set":
                logger.error("[G9] USPS client credentials not configured")
                return {
                    "gap_id": "G9",
                    "gap_name": "USPS Address Validation",
                    "status": "credentials_missing",
                    "error": "USPS client credentials not set",
                    "warnings": [
                        "Set USPS_CLIENT_ID and USPS_CLIENT_SECRET environment variables"
                    ],
                    "original_address": {
                        "street": street_address,
                        "city": city,
                        "state": state,
                        "zip": zip_code
                    }
                }
            else:
                logger.error(f"[G9] USPS validation failed: {result.error}")
                return {
                    "gap_id": "G9",
                    "gap_name": "USPS Address Validation",
                    "status": "validation_failed",
                    "error": result.error,
                    "original_address": {
                        "street": street_address,
                        "city": city,
                        "state": state,
                        "zip": zip_code
                    }
                }
        
        # Success - address validated
        logger.info(f"[G9] Address validated successfully")
        logger.info(f"[G9] DPV Confirmation: {result.dpv_confirmation}")
        
        return {
            "gap_id": "G9",
            "gap_name": "USPS Address Validation",
            "status": "validated",
            "original_address": {
                "street": street_address,
                "city": city,
                "state": state,
                "zip": zip_code
            },
            "standardized_address": result.standardized_address,
            "delivery_point": result.delivery_point,
            "carrier_route": result.carrier_route,
            "dpv_confirmation": result.dpv_confirmation,
            "dpv_cmra": result.dpv_cmra,
            "business": result.business,
            "central_delivery_point": result.central_delivery_point,
            "vacant": result.vacant,
            "warnings": result.warnings or [],
        }
        
    except Exception as e:
        logger.error(f"[G9] Error validating USPS address: {e}")
        return {
            "gap_id": "G9",
            "status": "error",
            "error": str(e),
        }


# Export all validation tools
form_validation_tools = [
    validate_fact_act_checkboxes,
    validate_urla_part1,
    validate_lo_nmls_info,
    validate_borrower_summary,
    check_disclosure_comments,
    validate_credit_by_purpose,
    validate_consent_validity,
    validate_company_license,
    verify_usps_address,
]

