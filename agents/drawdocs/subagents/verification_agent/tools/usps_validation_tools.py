"""
USPS Address Validation Tool for DrawDocs Verification Agent.

Validates subject property and borrower addresses against USPS API.
Generates PTF conditions if addresses are invalid or need standardization.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from packages.shared.usps_validator import get_usps_validator, validate_address_sync
from agents.drawdocs.tools.primitives import read_fields, add_ptf_condition, log_issue

logger = logging.getLogger(__name__)


def validate_usps_addresses(loan_id: str) -> Dict[str, Any]:
    """
    Validate loan addresses using USPS Address API v3.
    
    Validates:
    - Subject property address (fields 11, 12, 14, 15)
    - Borrower present address (fields FR0104, FR0105, FR0106, FR0107)
    - Mailing address if different (fields 98, 99, 100, 101)
    
    Creates PTF conditions for:
    - Invalid addresses (DPV = N)
    - Missing secondary units (DPV = D)
    - Vacant properties
    - Commercial Mail Receiving Agencies (mail drops)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results:
        {
            "status": "success" | "failed" | "credentials_missing",
            "addresses_validated": int,
            "addresses_passed": int,
            "addresses_flagged": int,
            "results": {
                "subject_property": {...},
                "borrower_present": {...},
                "mailing": {...}
            },
            "ptf_conditions_added": int,
            "error": Optional[str]
        }
    """
    logger.info(f"[USPS] Starting address validation for loan {loan_id}")
    
    # Check if validator is enabled
    validator = get_usps_validator()
    
    if not validator.enabled:
        logger.warning("[USPS] Validator disabled - credentials not configured")
        log_issue(
            loan_id=loan_id,
            severity="warning",
            message="USPS address validation skipped - credentials not configured",
            details={"action": "Set USPS_CLIENT_ID and USPS_CLIENT_SECRET in .env"}
        )
        return {
            "status": "credentials_missing",
            "addresses_validated": 0,
            "addresses_passed": 0,
            "addresses_flagged": 0,
            "results": {},
            "ptf_conditions_added": 0,
            "error": "USPS credentials not configured"
        }
    
    # Initialize result tracking
    result = {
        "status": "success",
        "addresses_validated": 0,
        "addresses_passed": 0,
        "addresses_flagged": 0,
        "results": {},
        "ptf_conditions_added": 0,
        "error": None
    }
    
    # =========================================================================
    # VALIDATE SUBJECT PROPERTY ADDRESS
    # =========================================================================
    
    logger.info("[USPS] Validating subject property address...")
    
    try:
        subject_fields = ["11", "12", "14", "15"]  # Street, City, State, ZIP
        subject_values = read_fields(loan_id, subject_fields)
        
        subject_street = subject_values.get("11")
        subject_city = subject_values.get("12")
        subject_state = subject_values.get("14")
        subject_zip = subject_values.get("15")
        
        if subject_street and subject_city and subject_state and subject_zip:
            logger.info(f"[USPS] Subject property: {subject_street}, {subject_city}, {subject_state} {subject_zip}")
            
            usps_result = validate_address_sync(
                street_address=subject_street,
                city=subject_city,
                state=subject_state,
                zip_code=subject_zip
            )
            
            result["addresses_validated"] += 1
            result["results"]["subject_property"] = {
                "original": {
                    "street": subject_street,
                    "city": subject_city,
                    "state": subject_state,
                    "zip": subject_zip
                },
                "validation": _process_usps_result(loan_id, "Subject Property", usps_result, result)
            }
        else:
            logger.warning("[USPS] Subject property address incomplete - skipping")
            result["results"]["subject_property"] = {
                "status": "skipped",
                "reason": "Incomplete address in Encompass"
            }
    except Exception as e:
        logger.error(f"[USPS] Failed to read subject property fields: {e}")
        result["results"]["subject_property"] = {
            "status": "error",
            "reason": f"Failed to read fields: {e}"
        }
    
    # =========================================================================
    # VALIDATE BORROWER PRESENT ADDRESS
    # =========================================================================
    
    logger.info("[USPS] Validating borrower present address...")
    
    try:
        borrower_fields = ["FR0104"]  # Borrower Present Address (single field in new format)
        borrower_values = read_fields(loan_id, borrower_fields)
        
        borrower_address = borrower_values.get("FR0104")
        
        if borrower_address:
            # Parse address (assuming format: "Street, City, State ZIP")
            parsed = _parse_address(borrower_address)
            
            if parsed["street"]:
                logger.info(f"[USPS] Borrower present: {borrower_address}")
                
                usps_result = validate_address_sync(
                    street_address=parsed["street"],
                    city=parsed["city"],
                    state=parsed["state"],
                    zip_code=parsed["zip"]
                )
                
                result["addresses_validated"] += 1
                result["results"]["borrower_present"] = {
                    "original": borrower_address,
                    "parsed": parsed,
                    "validation": _process_usps_result(loan_id, "Borrower Present Address", usps_result, result)
                }
            else:
                logger.warning("[USPS] Could not parse borrower present address")
                result["results"]["borrower_present"] = {
                    "status": "skipped",
                    "reason": "Could not parse address"
                }
        else:
            logger.warning("[USPS] Borrower present address not populated")
            result["results"]["borrower_present"] = {
                "status": "skipped",
                "reason": "Not populated in Encompass"
            }
    except Exception as e:
        logger.error(f"[USPS] Failed to read borrower address fields: {e}")
        result["results"]["borrower_present"] = {
            "status": "error",
            "reason": f"Failed to read fields: {e}"
        }
    
    # =========================================================================
    # VALIDATE MAILING ADDRESS (if different)
    # =========================================================================
    
    logger.info("[USPS] Validating mailing address...")
    
    try:
        mailing_fields = ["98", "99", "100", "101"]  # Mailing Street, City, State, ZIP
        mailing_values = read_fields(loan_id, mailing_fields)
        
        mailing_street = mailing_values.get("98")
        mailing_city = mailing_values.get("99")
        mailing_state = mailing_values.get("100")
        mailing_zip = mailing_values.get("101")
        
        if mailing_street and mailing_city and mailing_state and mailing_zip:
            # Only validate if different from borrower present address
            if mailing_street != borrower_address:
                logger.info(f"[USPS] Mailing address: {mailing_street}, {mailing_city}, {mailing_state} {mailing_zip}")
                
                usps_result = validate_address_sync(
                    street_address=mailing_street,
                    city=mailing_city,
                    state=mailing_state,
                    zip_code=mailing_zip
                )
                
                result["addresses_validated"] += 1
                result["results"]["mailing"] = {
                    "original": {
                        "street": mailing_street,
                        "city": mailing_city,
                        "state": mailing_state,
                        "zip": mailing_zip
                    },
                    "validation": _process_usps_result(loan_id, "Mailing Address", usps_result, result)
                }
            else:
                logger.info("[USPS] Mailing address same as borrower present - skipping")
                result["results"]["mailing"] = {
                    "status": "skipped",
                    "reason": "Same as borrower present address"
                }
        else:
            logger.info("[USPS] Mailing address not populated or incomplete")
            result["results"]["mailing"] = {
                "status": "skipped",
                "reason": "Not populated or incomplete"
            }
    except Exception as e:
        logger.error(f"[USPS] Failed to read mailing address fields: {e}")
        result["results"]["mailing"] = {
            "status": "error",
            "reason": f"Failed to read fields: {e}"
        }
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    logger.info(f"[USPS] Address validation complete:")
    logger.info(f"  - Addresses validated: {result['addresses_validated']}")
    logger.info(f"  - Addresses passed: {result['addresses_passed']}")
    logger.info(f"  - Addresses flagged: {result['addresses_flagged']}")
    logger.info(f"  - PTF conditions added: {result['ptf_conditions_added']}")
    
    return result


def _process_usps_result(
    loan_id: str,
    address_type: str,
    usps_result: Any,
    tracking: Dict
) -> Dict[str, Any]:
    """
    Process USPS validation result and create PTF conditions if needed.
    
    Args:
        loan_id: Encompass loan GUID
        address_type: Type of address (e.g., "Subject Property")
        usps_result: USPSAddressResult from validator
        tracking: Result tracking dictionary (updates in-place)
        
    Returns:
        Validation result dictionary
    """
    if not usps_result.success:
        logger.error(f"[USPS] {address_type} validation failed: {usps_result.error}")
        
        # Add PTF for validation failure
        ptf_result = add_ptf_condition(
            loan_id=loan_id,
            category="Address Validation",
            description=f"{address_type} failed USPS validation: {usps_result.error}",
            severity="PTF",
            assigned_to="Loan Processor"
        )
        
        if ptf_result["success"]:
            tracking["ptf_conditions_added"] += 1
        
        tracking["addresses_flagged"] += 1
        
        return {
            "status": "failed",
            "error": usps_result.error,
            "ptf_added": ptf_result["success"],
            "ptf_condition_id": ptf_result.get("condition_id")
        }
    
    # Success - check validation flags
    validation_result = {
        "status": "validated",
        "standardized_address": usps_result.standardized_address,
        "dpv_confirmation": usps_result.dpv_confirmation,
        "dpv_cmra": usps_result.dpv_cmra,
        "business": usps_result.business,
        "vacant": usps_result.vacant,
        "warnings": usps_result.warnings or [],
        "ptf_conditions": []
    }
    
    # Check for issues that require PTF conditions
    ptf_needed = []
    
    # 1. DPV Confirmation
    if usps_result.dpv_confirmation == "N":
        ptf_needed.append({
            "category": "Address Validation",
            "description": f"{address_type} not confirmed by USPS - verify address with borrower and title company",
            "severity": "PTF"
        })
    elif usps_result.dpv_confirmation == "D":
        ptf_needed.append({
            "category": "Address Validation",
            "description": f"{address_type} missing secondary unit (apt/suite) - verify with borrower",
            "severity": "PTF"
        })
    
    # 2. Vacant Property
    if usps_result.vacant == "Y":
        ptf_needed.append({
            "category": "Property Status",
            "description": f"{address_type} marked as vacant by USPS - verify occupancy status",
            "severity": "PTF"
        })
    
    # 3. Commercial Mail Receiving Agency (Mail Drop)
    if usps_result.dpv_cmra == "Y":
        ptf_needed.append({
            "category": "Address Validation",
            "description": f"{address_type} is a Commercial Mail Receiving Agency (CMRA/mail drop) - verify borrower residence",
            "severity": "PTF"
        })
    
    # Add PTF conditions
    for ptf_data in ptf_needed:
        ptf_result = add_ptf_condition(
            loan_id=loan_id,
            category=ptf_data["category"],
            description=ptf_data["description"],
            severity=ptf_data["severity"],
            assigned_to="Loan Processor"
        )
        
        if ptf_result["success"]:
            tracking["ptf_conditions_added"] += 1
            validation_result["ptf_conditions"].append({
                "condition_id": ptf_result.get("condition_id"),
                "description": ptf_data["description"]
            })
    
    # Update tracking
    if ptf_needed:
        tracking["addresses_flagged"] += 1
        logger.warning(f"[USPS] {address_type}: {len(ptf_needed)} PTF condition(s) added")
    else:
        tracking["addresses_passed"] += 1
        logger.info(f"[USPS] {address_type}: Validated successfully (DPV={usps_result.dpv_confirmation})")
    
    return validation_result


def _parse_address(full_address: str) -> Dict[str, Optional[str]]:
    """
    Parse a full address string into components.
    
    Attempts to parse: "Street, City, State ZIP"
    
    Args:
        full_address: Full address string
        
    Returns:
        Dictionary with street, city, state, zip (may have None values)
    """
    result = {
        "street": None,
        "city": None,
        "state": None,
        "zip": None
    }
    
    if not full_address:
        return result
    
    try:
        # Simple parsing - assumes format: "Street, City, State ZIP"
        parts = full_address.split(",")
        
        if len(parts) >= 2:
            result["street"] = parts[0].strip()
            
            # Last part should be "City State ZIP"
            last_part = parts[-1].strip()
            tokens = last_part.split()
            
            if len(tokens) >= 3:
                result["zip"] = tokens[-1]
                result["state"] = tokens[-2]
                result["city"] = " ".join(tokens[:-2])
            elif len(tokens) == 2:
                result["state"] = tokens[0]
                result["zip"] = tokens[1]
    
    except Exception as e:
        logger.warning(f"[USPS] Failed to parse address '{full_address}': {e}")
    
    return result


