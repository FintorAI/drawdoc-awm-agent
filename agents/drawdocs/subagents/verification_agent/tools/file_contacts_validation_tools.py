"""
File Contacts Validation Tools.

Implements SOP Step 9: File Contacts validation and verification.

Per SOP:
- Lender: Fixed values (ALL WESTERN MORTGAGE, INC.)
- Investor: Selected from Business Contact when investor is locked in Reg-Z CD
- Title Insurance Company: Verify from Title Report
- Escrow Company: Verify from Title Report and Wire Instructions
- Settlement Agent: Copy from Title/Escrow when same
- Hazard Insurance: Already handled in insurance validation
- Flood Insurance: Already handled in insurance validation
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

class FileContactsFields:
    """Encompass field IDs for File Contacts validation."""
    
    # Lender Information (Fixed values per SOP)
    LENDER_NAME = "1264"  # Lender Name
    LENDER_PHONE = "1262"  # Lender Phone
    LENDER_ADDRESS = "319"  # Lender Address
    LENDER_CITY = "313"  # Lender City
    LENDER_STATE = "321"  # Lender State
    LENDER_ZIP = "323"  # Lender Zip
    LENDER_NMLS = "3244"  # Lender NMLS
    LENDER_LIC_ID = "3032"  # Lender License ID
    LENDER_EMAIL = "95"  # Lender Email (LO's email)
    LENDER_FAX = "1263"  # Lender Fax
    
    # Investor
    INVESTOR_NAME = "VEND.X263"  # Investor Name
    
    # Title Insurance Company
    TITLE_COMPANY_NAME = "411"  # Title Insurance Company Name
    TITLE_CONTACT = "416"  # Title Co Contact
    TITLE_PHONE = "417"  # Title Co Phone
    TITLE_OFFICER_NAME = "4502"  # Title Officer Title
    TITLE_OFFICER_EMAIL = "88"  # Title Officer Email
    
    # Escrow Company
    ESCROW_COMPANY_NAME = "610"  # Escrow Company Name
    ESCROW_CONTACT = "611"  # Escrow Co Contact
    ESCROW_PHONE = "615"  # Escrow Co Phone
    ESCROW_CASE_NUMBER = "186"  # Escrow Case Number
    ESCROW_LICENSE_ID = "VEND.X986"  # Escrow Company License ID#
    ESCROW_OFFICER_LICENSE = "VEND.X703"  # Escrow Officer License#
    ESCROW_BANK_ABA = "VEND.X396"  # Escrow Bank ABA
    ESCROW_BANK_ACCOUNT = "VEND.X397"  # Escrow Bank Account
    
    # Settlement Agent
    SETTLEMENT_AGENT_NAME = "395"  # Doc Signing Company Name
    SETTLEMENT_AGENT_CONTACT = "VEND.X195"  # Doc Signing Co Contact Name
    SETTLEMENT_AGENT_PHONE = "VEND.X196"  # Doc Signing Co Phone
    COPY_TO_SETTLEMENT_AGENT = None  # Copy to Settlement Agent checkbox - need Field ID


# =============================================================================
# FIXED VALUES (Per SOP)
# =============================================================================

LENDER_REQUIRED_VALUES = {
    "name": "ALL WESTERN MORTGAGE, INC.",
    "address": "8345 WEST SUNSET ROAD, SUITE 380",
    "city": "LAS VEGAS",
    "state": "NV",
    "zip": "89113",
    "org_state": "Nevada",
    "nmls": "14210",
    "lic_id": "204",
    "phone": "702-369-0905",
    "fax": "702-920-8421"
}


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_file_contacts(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive File Contacts validation per SOP Step 9.
    
    Validates:
    1. Lender Information (fixed values)
    2. Investor Selection (from Business Contact)
    3. Title Insurance Company (verify from Title Report)
    4. Escrow Company (verify from Title Report and Wire Instructions)
    5. Settlement Agent (copy logic when same as Title/Escrow)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"[FILE CONTACTS] Starting File Contacts validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "validations": {},
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[FILE CONTACTS] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        # Read File Contacts fields
        fields = read_fields(loan_id, [
            FileContactsFields.LENDER_NAME,
            FileContactsFields.LENDER_PHONE,
            FileContactsFields.LENDER_ADDRESS,
            FileContactsFields.LENDER_CITY,
            FileContactsFields.LENDER_STATE,
            FileContactsFields.LENDER_ZIP,
            FileContactsFields.LENDER_NMLS,
            FileContactsFields.LENDER_LIC_ID,
            FileContactsFields.LENDER_EMAIL,
            FileContactsFields.LENDER_FAX,
            FileContactsFields.INVESTOR_NAME,
            FileContactsFields.TITLE_COMPANY_NAME,
            FileContactsFields.TITLE_CONTACT,
            FileContactsFields.TITLE_PHONE,
            FileContactsFields.TITLE_OFFICER_NAME,
            FileContactsFields.TITLE_OFFICER_EMAIL,
            FileContactsFields.ESCROW_COMPANY_NAME,
            FileContactsFields.ESCROW_CONTACT,
            FileContactsFields.ESCROW_PHONE,
            FileContactsFields.ESCROW_CASE_NUMBER,
            FileContactsFields.ESCROW_LICENSE_ID,
            FileContactsFields.ESCROW_OFFICER_LICENSE,
            FileContactsFields.ESCROW_BANK_ABA,
            FileContactsFields.ESCROW_BANK_ACCOUNT,
            FileContactsFields.SETTLEMENT_AGENT_NAME,
            FileContactsFields.SETTLEMENT_AGENT_CONTACT,
            FileContactsFields.SETTLEMENT_AGENT_PHONE,
        ])
        
        # =====================================================================
        # 1. LENDER INFORMATION VALIDATION
        # =====================================================================
        logger.info("[FILE CONTACTS] Validating Lender information...")
        lender_validation = validate_lender_information(loan_id, fields)
        result["validations"]["lender"] = lender_validation
        
        if not lender_validation.get("passed"):
            for violation in lender_validation.get("violations", []):
                result["violations"].append(violation)
        
        # =====================================================================
        # 2. INVESTOR VALIDATION
        # =====================================================================
        logger.info("[FILE CONTACTS] Validating Investor selection...")
        investor_validation = validate_investor_selection(loan_id, fields)
        result["validations"]["investor"] = investor_validation
        
        if not investor_validation.get("passed"):
            for violation in investor_validation.get("violations", []):
                result["violations"].append(violation)
        
        # =====================================================================
        # 3. TITLE INSURANCE COMPANY VALIDATION
        # =====================================================================
        logger.info("[FILE CONTACTS] Validating Title Insurance Company...")
        title_validation = validate_title_company(loan_id, fields)
        result["validations"]["title"] = title_validation
        
        if not title_validation.get("passed"):
            for violation in title_validation.get("violations", []):
                result["violations"].append(violation)
        
        # =====================================================================
        # 4. ESCROW COMPANY VALIDATION
        # =====================================================================
        logger.info("[FILE CONTACTS] Validating Escrow Company...")
        escrow_validation = validate_escrow_company(loan_id, fields)
        result["validations"]["escrow"] = escrow_validation
        
        if not escrow_validation.get("passed"):
            for violation in escrow_validation.get("violations", []):
                result["violations"].append(violation)
        
        # =====================================================================
        # 5. SETTLEMENT AGENT VALIDATION
        # =====================================================================
        logger.info("[FILE CONTACTS] Validating Settlement Agent...")
        settlement_validation = validate_settlement_agent(loan_id, fields)
        result["validations"]["settlement_agent"] = settlement_validation
        
        if not settlement_validation.get("passed"):
            for violation in settlement_validation.get("violations", []):
                result["violations"].append(violation)
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        all_passed = all(
            validation.get("passed", True)
            for validation in result["validations"].values()
        )
        
        result["status"] = "complete" if all_passed else "violations_found"
        result["details"].append(f"Validations: {len(result['validations'])}")
        result["details"].append(f"Violations: {len(result['violations'])}")
        result["details"].append(f"Warnings: {len(result['warnings'])}")
        
        if all_passed:
            logger.info("\n" + "="*80)
            logger.info(f"[FILE CONTACTS] ✅ ALL FILE CONTACTS VALIDATIONS PASSED")
            logger.info("="*80)
        else:
            logger.warning("\n" + "="*80)
            logger.warning(f"[FILE CONTACTS] ⚠️  Found {len(result['violations'])} violations")
            logger.warning("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"[FILE CONTACTS] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# INDIVIDUAL VALIDATION FUNCTIONS
# =============================================================================

def validate_lender_information(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Lender information matches fixed values.
    
    Per SOP:
    - Lender name: ALL WESTERN MORTGAGE, INC.
    - Address: 8345 WEST SUNSET ROAD, SUITE 380, LAS VEGAS, NV 89113
    - Org. State: Nevada (always)
    - NMLS: 14210
    - LIC ID: 204
    - Phone: 702-369-0905
    - Fax: 702-920-8421
    - Email: LO's email id (variable)
    
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
    
    lender_name = fields.get(FileContactsFields.LENDER_NAME, "").strip().upper()
    lender_phone = fields.get(FileContactsFields.LENDER_PHONE, "").strip()
    lender_address = fields.get(FileContactsFields.LENDER_ADDRESS, "").strip()
    lender_city = fields.get(FileContactsFields.LENDER_CITY, "").strip()
    lender_state = fields.get(FileContactsFields.LENDER_STATE, "").strip()
    lender_zip = fields.get(FileContactsFields.LENDER_ZIP, "").strip()
    lender_nmls = fields.get(FileContactsFields.LENDER_NMLS, "").strip()
    lender_lic_id = fields.get(FileContactsFields.LENDER_LIC_ID, "").strip()
    lender_fax = fields.get(FileContactsFields.LENDER_FAX, "").strip()
    
    # Check Lender Name
    if lender_name != LENDER_REQUIRED_VALUES["name"].upper():
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Lender Information",
            "field": "Lender Name",
            "message": f"Lender name must be '{LENDER_REQUIRED_VALUES['name']}' but found '{lender_name}'",
            "action_required": f"Update Lender name to '{LENDER_REQUIRED_VALUES['name']}' or select from Business contacts",
            "fields_affected": [FileContactsFields.LENDER_NAME],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender Phone
    if lender_phone != LENDER_REQUIRED_VALUES["phone"]:
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender Phone",
            "message": f"Lender phone must be '{LENDER_REQUIRED_VALUES['phone']}' but found '{lender_phone}'",
            "action_required": f"Update Lender phone to '{LENDER_REQUIRED_VALUES['phone']}'",
            "fields_affected": [FileContactsFields.LENDER_PHONE],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender Address
    if lender_address and lender_address.upper() != LENDER_REQUIRED_VALUES["address"].upper():
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender Address",
            "message": f"Lender address should be '{LENDER_REQUIRED_VALUES['address']}' but found '{lender_address}'",
            "action_required": f"Update Lender address to '{LENDER_REQUIRED_VALUES['address']}'",
            "fields_affected": [FileContactsFields.LENDER_ADDRESS],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender City
    if lender_city and lender_city.upper() != LENDER_REQUIRED_VALUES["city"].upper():
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender City",
            "message": f"Lender city should be '{LENDER_REQUIRED_VALUES['city']}' but found '{lender_city}'",
            "action_required": f"Update Lender city to '{LENDER_REQUIRED_VALUES['city']}'",
            "fields_affected": [FileContactsFields.LENDER_CITY],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender State
    if lender_state and lender_state.upper() != LENDER_REQUIRED_VALUES["state"].upper():
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender State",
            "message": f"Lender state should be '{LENDER_REQUIRED_VALUES['state']}' but found '{lender_state}'",
            "action_required": f"Update Lender state to '{LENDER_REQUIRED_VALUES['state']}'",
            "fields_affected": [FileContactsFields.LENDER_STATE],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender Zip
    if lender_zip and lender_zip != LENDER_REQUIRED_VALUES["zip"]:
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender Zip",
            "message": f"Lender zip should be '{LENDER_REQUIRED_VALUES['zip']}' but found '{lender_zip}'",
            "action_required": f"Update Lender zip to '{LENDER_REQUIRED_VALUES['zip']}'",
            "fields_affected": [FileContactsFields.LENDER_ZIP],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender NMLS
    if lender_nmls and lender_nmls != LENDER_REQUIRED_VALUES["nmls"]:
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Lender Information",
            "field": "Lender NMLS",
            "message": f"Lender NMLS must be '{LENDER_REQUIRED_VALUES['nmls']}' but found '{lender_nmls}'",
            "action_required": f"Update Lender NMLS to '{LENDER_REQUIRED_VALUES['nmls']}'",
            "fields_affected": [FileContactsFields.LENDER_NMLS],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender License ID
    if lender_lic_id and lender_lic_id != LENDER_REQUIRED_VALUES["lic_id"]:
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Lender Information",
            "field": "Lender License ID",
            "message": f"Lender License ID must be '{LENDER_REQUIRED_VALUES['lic_id']}' but found '{lender_lic_id}'",
            "action_required": f"Update Lender License ID to '{LENDER_REQUIRED_VALUES['lic_id']}'",
            "fields_affected": [FileContactsFields.LENDER_LIC_ID],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    # Check Lender Fax
    if lender_fax and lender_fax != LENDER_REQUIRED_VALUES["fax"]:
        result["violations"].append({
            "type": "PTF",
            "severity": "MEDIUM",
            "category": "Lender Information",
            "field": "Lender Fax",
            "message": f"Lender fax should be '{LENDER_REQUIRED_VALUES['fax']}' but found '{lender_fax}'",
            "action_required": f"Update Lender fax to '{LENDER_REQUIRED_VALUES['fax']}'",
            "fields_affected": [FileContactsFields.LENDER_FAX],
            "sop_reference": "SOP Step 9 - Lender Information"
        })
        result["passed"] = False
    
    if result["violations"]:
        result["message"] = f"Found {len(result['violations'])} lender information violations"
    else:
        result["message"] = "Lender information validated"
    
    return result


def validate_investor_selection(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Investor selection.
    
    Per SOP:
    - Investor information must be selected from Business Contact when investor is selected/locked in Reg-Z CD form
    - No need to update if there is No Investor
    
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
    
    investor_name = fields.get(FileContactsFields.INVESTOR_NAME, "").strip()
    
    # TODO: Need to check if investor is selected/locked in Reg-Z CD form
    # For now, if investor name is present, validate it's not empty
    # If investor is in Reg-Z CD but not in File Contacts, that's a violation
    
    if investor_name:
        result["details"]["investor_name"] = investor_name
        result["message"] = f"Investor selected: {investor_name}"
    else:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Investor name not found - verify if investor is selected/locked in Reg-Z CD form",
            "action_required": "If investor is in Reg-Z CD form, select Investor from Business Contact"
        })
        result["message"] = "No investor selected (verify if required)"
    
    return result


def validate_title_company(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Title Insurance Company information.
    
    Per SOP:
    1. Verify Title Company details from preliminary title report
    2. Verify Title Officer and Email from Title report
    3. Ensure Loan amount on Title Report matches
    4. ALTA/ATIMA clause has Lender name as "ALL WESTERN MORTGAGE, INC."
    
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
    
    title_company_name = fields.get(FileContactsFields.TITLE_COMPANY_NAME, "").strip()
    title_contact = fields.get(FileContactsFields.TITLE_CONTACT, "").strip()
    title_phone = fields.get(FileContactsFields.TITLE_PHONE, "").strip()
    
    # Check if Title Company is populated
    if not title_company_name:
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Title Insurance Company",
            "field": "Title Company Name",
            "message": "Title Company Name is missing",
            "action_required": "Update Title Company information from Title Report",
            "fields_affected": [FileContactsFields.TITLE_COMPANY_NAME],
            "sop_reference": "SOP Step 9 - Title Insurance Company"
        })
        result["passed"] = False
    
    # Check Title Officer (if field ID available)
    if FileContactsFields.TITLE_OFFICER_NAME:
        title_officer = fields.get(FileContactsFields.TITLE_OFFICER_NAME, "").strip()
        if not title_officer:
            result["warnings"].append({
                "type": "WARNING",
                "message": "Title Officer Name not found - verify from Title Report",
                "action_required": "Update Title Officer Name from Title Report"
            })
    else:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Title Officer Name and Email field IDs not found - manual verification required",
            "action_required": "Manually verify Title Officer and Email from Title Report"
        })
    
    result["details"]["title_company_name"] = title_company_name
    result["details"]["title_contact"] = title_contact
    
    if result["violations"]:
        result["message"] = f"Found {len(result['violations'])} title company violations"
    else:
        result["message"] = "Title Company information validated (manual verification of Title Report recommended)"
    
    return result


def validate_escrow_company(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Escrow Company information.
    
    Per SOP:
    1. Verify Escrow company details from Title report
    2. Update Bank ABA and Bank Account from Escrow wire instruction
    3. Verify Escrow Company License ID# and Escrow Officer License#
    4. Verify Name, address, Officer Name, Escrow Case#, Phone & Email from Prelim Title report
    
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
    
    escrow_company_name = fields.get(FileContactsFields.ESCROW_COMPANY_NAME, "").strip()
    escrow_contact = fields.get(FileContactsFields.ESCROW_CONTACT, "").strip()
    escrow_phone = fields.get(FileContactsFields.ESCROW_PHONE, "").strip()
    escrow_case_number = fields.get(FileContactsFields.ESCROW_CASE_NUMBER, "").strip()
    escrow_license_id = fields.get(FileContactsFields.ESCROW_LICENSE_ID, "").strip()
    escrow_officer_license = fields.get(FileContactsFields.ESCROW_OFFICER_LICENSE, "").strip()
    escrow_bank_aba = fields.get(FileContactsFields.ESCROW_BANK_ABA, "").strip()
    escrow_bank_account = fields.get(FileContactsFields.ESCROW_BANK_ACCOUNT, "").strip()
    
    # Check if Escrow Company is populated
    if not escrow_company_name:
        result["violations"].append({
            "type": "PTF",
            "severity": "HIGH",
            "category": "Escrow Company",
            "field": "Escrow Company Name",
            "message": "Escrow Company Name is missing",
            "action_required": "Update Escrow Company information from Title Report",
            "fields_affected": [FileContactsFields.ESCROW_COMPANY_NAME],
            "sop_reference": "SOP Step 9 - Escrow Company"
        })
        result["passed"] = False
    
    # Check Escrow License IDs
    if not escrow_license_id:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Escrow Company License ID# not found - verify from Title Report",
            "action_required": "Update Escrow Company License ID# from Title Report"
        })
    
    if not escrow_officer_license:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Escrow Officer License# not found - verify from Title Report",
            "action_required": "Update Escrow Officer License# from Title Report"
        })
    
    # Check Bank ABA and Account
    if not escrow_bank_aba:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Escrow Bank ABA not found - verify from Wire Instructions",
            "action_required": "Update Bank ABA from Escrow wire instructions"
        })
    
    if not escrow_bank_account:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Escrow Bank Account not found - verify from Wire Instructions",
            "action_required": "Update Bank Account from Escrow wire instructions"
        })
    
    result["details"]["escrow_company_name"] = escrow_company_name
    result["details"]["escrow_contact"] = escrow_contact
    result["details"]["escrow_case_number"] = escrow_case_number
    
    if result["violations"]:
        result["message"] = f"Found {len(result['violations'])} escrow company violations"
    else:
        result["message"] = "Escrow Company information validated (manual verification of Title Report and Wire Instructions recommended)"
    
    return result


def validate_settlement_agent(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Settlement Agent information.
    
    Per SOP:
    - Copy to Settlement Agent checkbox should be checked when Settlement & Title Company are same
    - If Title & Escrow Company is different, then Escrow Company Information will be copied to Settlement Agent
    - Verify "Add to CD Contact Info" is checked as YES
    
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
    
    settlement_agent_name = fields.get(FileContactsFields.SETTLEMENT_AGENT_NAME, "").strip()
    title_company_name = fields.get(FileContactsFields.TITLE_COMPANY_NAME, "").strip()
    escrow_company_name = fields.get(FileContactsFields.ESCROW_COMPANY_NAME, "").strip()
    
    # Check if Settlement Agent matches Title or Escrow
    if settlement_agent_name:
        if title_company_name and settlement_agent_name.upper() == title_company_name.upper():
            result["details"]["copy_from"] = "Title Company"
            result["message"] = "Settlement Agent matches Title Company - verify 'Copy to Settlement Agent' checkbox is checked"
        elif escrow_company_name and settlement_agent_name.upper() == escrow_company_name.upper():
            result["details"]["copy_from"] = "Escrow Company"
            result["message"] = "Settlement Agent matches Escrow Company"
        else:
            result["warnings"].append({
                "type": "WARNING",
                "message": "Settlement Agent does not match Title or Escrow Company - verify if correct",
                "action_required": "Verify Settlement Agent information matches Title or Escrow Company"
            })
    else:
        result["warnings"].append({
            "type": "WARNING",
            "message": "Settlement Agent name not found",
            "action_required": "Update Settlement Agent information (copy from Title or Escrow Company if same)"
        })
    
    # Check "Add to CD Contact Info" (if field ID available)
    result["warnings"].append({
        "type": "WARNING",
        "message": "Verify 'Add to CD Contact Info' is checked as YES",
        "action_required": "Check 'Add to CD Contact Info' checkbox in Settlement Agent section"
    })
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_file_contacts",
    "validate_lender_information",
    "validate_investor_selection",
    "validate_title_company",
    "validate_escrow_company",
    "validate_settlement_agent",
]

