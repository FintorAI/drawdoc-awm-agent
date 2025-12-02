"""Form validation tools for disclosure verification agent.

Per Disclosure Desk SOP (v2):
- Validate 1003 URLA Lender Form (all 4 parts)
- Validate Borrower Summary Origination
- Validate FACT Act Disclosure
- Validate RegZ-LE fields
- Validate LO NMLS info
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared import (
    validate_disclosure_forms,
    validate_single_form,
    get_form_validator,
)

logger = logging.getLogger(__name__)


@tool
def validate_disclosure_form_fields(loan_id: str) -> dict:
    """Validate all required form fields for disclosure.
    
    Per SOP, validates:
    - 1003 URLA Lender Form (all 4 parts)
    - Borrower Summary Origination
    - FACT Act Disclosure (credit scores)
    - RegZ-LE fields
    - Affiliated Business Arrangements
    - LO Info (NMLS verification)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - all_valid: Whether all forms passed validation
        - forms_checked: Number of forms checked
        - forms_passed: Number of forms that passed
        - total_fields: Total fields checked
        - valid_fields: Number of valid fields
        - missing_critical: List of critical missing fields (blocking)
        - missing_fields: List of all missing fields
        - form_results: Detailed results per form
        - blocking: Whether this blocks disclosure
    """
    logger.info(f"[FORM] Validating all disclosure forms for loan {loan_id[:8]}...")
    
    try:
        result = validate_disclosure_forms(loan_id)
        
        logger.info(f"[FORM] Validation complete: {result.get('forms_passed')}/{result.get('forms_checked')} forms passed")
        
        if result.get("missing_critical"):
            logger.warning(f"[FORM] Missing critical fields: {result.get('missing_critical')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FORM] Error validating forms: {e}")
        return {
            "all_valid": False,
            "error": str(e),
            "blocking": True,
        }


@tool
def validate_form_by_name(loan_id: str, form_name: str) -> dict:
    """Validate a specific form's fields.
    
    Available forms:
    - 1003_URLA_Lender
    - 1003_URLA_Part1
    - 1003_URLA_Part2
    - 1003_URLA_Part4
    - Borrower_Summary_Origination
    - FACT_Act_Disclosure
    - RegZ_LE
    - Affiliated_Business_Arrangements
    - LO_Info
    
    Args:
        loan_id: Encompass loan GUID
        form_name: Name of form to validate
        
    Returns:
        Dictionary with form validation results
    """
    logger.info(f"[FORM] Validating {form_name} for loan {loan_id[:8]}...")
    
    try:
        result = validate_single_form(loan_id, form_name)
        
        if result.get("all_valid"):
            logger.info(f"[FORM] {form_name}: All {result.get('field_count')} fields valid")
        else:
            logger.warning(f"[FORM] {form_name}: Missing {len(result.get('missing_fields', []))} fields")
        
        return result
        
    except Exception as e:
        logger.error(f"[FORM] Error validating {form_name}: {e}")
        return {
            "form_name": form_name,
            "all_valid": False,
            "error": str(e),
        }


@tool
def validate_lo_authorization(loan_id: str) -> dict:
    """Validate Loan Originator (LO) authorization.
    
    Per SOP:
    - Verify LO is authorized to conduct business in property state
    - Verify LO license is approved and renewed for current year
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with LO validation info:
        - lo_name: Loan Originator name
        - lo_nmls_id: LO NMLS ID
        - lo_company_name: Company name
        - lo_company_nmls: Company NMLS ID
        - property_state: Property state
        - warnings: Any warnings about LO info
        - needs_verification: Message about what to verify
    """
    logger.info(f"[FORM] Validating LO authorization for loan {loan_id[:8]}...")
    
    try:
        validator = get_form_validator()
        result = validator.validate_lo_info(loan_id)
        
        if result.get("warnings"):
            logger.warning(f"[FORM] LO warnings: {result.get('warnings')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FORM] Error validating LO: {e}")
        return {
            "error": str(e),
            "warnings": ["Error validating LO authorization"],
        }


@tool
def get_form_list() -> dict:
    """Get list of available forms for validation.
    
    Returns:
        Dictionary with available form names and descriptions
    """
    return {
        "forms": {
            "1003_URLA_Lender": "Basic borrower and loan info",
            "1003_URLA_Part1": "Current/mailing address verification",
            "1003_URLA_Part2": "Employment and income info",
            "1003_URLA_Part4": "LO info and declarations",
            "Borrower_Summary_Origination": "Channel, status, dates",
            "FACT_Act_Disclosure": "Credit score disclosure",
            "RegZ_LE": "LE date, rate, term",
            "Affiliated_Business_Arrangements": "Settlement/transaction boxes",
            "LO_Info": "LO NMLS verification",
        },
        "critical_forms": [
            "1003_URLA_Lender",
            "RegZ_LE",
            "LO_Info",
        ]
    }


# Export tools for agent registration
form_tools = [
    validate_disclosure_form_fields,
    validate_form_by_name,
    validate_lo_authorization,
    get_form_list,
]

