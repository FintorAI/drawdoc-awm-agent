"""
File Contacts Extraction Module

Extracts File Contacts information from loan documents for SOP Step 9.
This module handles extraction from:
- Title Report → Title Company details
- Wire Instructions → Bank/Escrow details
- Evidence of Insurance → Insurance Company details

Extracted data is added to field_mappings and written by Drawcore Agent Phase 6.

Based on: Docs Draw SOP Step 9 (Lines 241-292)
"""

from typing import Dict, List, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# FIELD ID MAPPINGS (From SOP and CSV)
# ============================================================================

FILE_CONTACTS_FIELDS = {
    # Lender Information (Fixed values - no extraction needed)
    "lender_name": {"id": "L1", "value": "ALL WESTERN MORTGAGE, INC."},
    "lender_address": {"id": "L2", "value": "8345 WEST SUNSET ROAD, SUITE 380"},
    "lender_city": {"id": "L3", "value": "LAS VEGAS"},
    "lender_state": {"id": "L4", "value": "NV"},
    "lender_zip": {"id": "L5", "value": "89113"},
    "lender_nmls": {"id": "L6", "value": "14210"},
    "lender_lic_id": {"id": "L7", "value": "204"},
    "lender_phone": {"id": "L8", "value": "702-369-0905"},
    "lender_fax": {"id": "L9", "value": "702-920-8421"},
    
    # Title Company (From Title Report)
    "title_company_name": {"id": "VEND.X100", "source": "Title Report"},
    "title_company_address": {"id": "VEND.X101", "source": "Title Report"},
    "title_company_city": {"id": "VEND.X102", "source": "Title Report"},
    "title_company_state": {"id": "VEND.X103", "source": "Title Report"},
    "title_company_zip": {"id": "VEND.X104", "source": "Title Report"},
    "title_officer_name": {"id": "VEND.X105", "source": "Title Report"},
    "title_officer_email": {"id": "VEND.X106", "source": "Title Report"},
    "title_officer_phone": {"id": "VEND.X107", "source": "Title Report"},
    
    # Escrow Company (From Title Report / Wire Instructions)
    "escrow_company_name": {"id": "186", "source": "Title Report"},  # From CSV
    "escrow_company_address": {"id": "VEND.X110", "source": "Title Report"},
    "escrow_company_city": {"id": "VEND.X111", "source": "Title Report"},
    "escrow_company_state": {"id": "VEND.X112", "source": "Title Report"},
    "escrow_company_zip": {"id": "VEND.X113", "source": "Title Report"},
    "escrow_officer_name": {"id": "VEND.X114", "source": "Title Report"},
    "escrow_officer_email": {"id": "VEND.X115", "source": "Title Report"},
    "escrow_officer_phone": {"id": "VEND.X116", "source": "Title Report"},
    "escrow_case_number": {"id": "186", "source": "Title Report"},  # From CSV
    "escrow_bank_aba": {"id": "VEND.X117", "source": "Wire Instructions"},
    "escrow_bank_account": {"id": "VEND.X118", "source": "Wire Instructions"},
    
    # Hazard Insurance Company (From Evidence of Insurance)
    "hazard_ins_company_name": {"id": "L252", "source": "Evidence of Insurance"},  # From CSV
    "hazard_ins_company_address": {"id": "VEND.X120", "source": "Evidence of Insurance"},
    "hazard_ins_agent_name": {"id": "VEND.X163", "source": "Evidence of Insurance"},  # From CSV
    "hazard_ins_agent_email": {"id": "VEND.X164", "source": "Evidence of Insurance"},  # From CSV
    "hazard_ins_agent_phone": {"id": "VEND.X121", "source": "Evidence of Insurance"},
    "hazard_ins_policy_number": {"id": "VEND.X122", "source": "Evidence of Insurance"},
}


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_from_title_report(document_text: str) -> Dict[str, Any]:
    """
    Extract Title Company and Escrow Company details from Title Report.
    
    Args:
        document_text: Full text content of Title Report
        
    Returns:
        Dictionary of extracted field values
    """
    extracted = {}
    
    logger.info("[FILE_CONTACTS] Extracting from Title Report...")
    
    # NOTE: These are placeholder regex patterns
    # In production, you'd use LandingAI or more sophisticated extraction
    
    # Try to find title company name
    title_match = re.search(r"Title Company:?\s*([^\n]+)", document_text, re.IGNORECASE)
    if title_match:
        extracted["title_company_name"] = title_match.group(1).strip()
    
    # Try to find escrow company name
    escrow_match = re.search(r"Escrow Company:?\s*([^\n]+)", document_text, re.IGNORECASE)
    if escrow_match:
        extracted["escrow_company_name"] = escrow_match.group(1).strip()
    
    # Try to find escrow case number
    case_match = re.search(r"Escrow (?:Number|#|Case):?\s*([A-Z0-9-]+)", document_text, re.IGNORECASE)
    if case_match:
        extracted["escrow_case_number"] = case_match.group(1).strip()
    
    # Try to find officer names
    officer_match = re.search(r"Officer:?\s*([^\n]+)", document_text, re.IGNORECASE)
    if officer_match:
        officer_name = officer_match.group(1).strip()
        extracted["title_officer_name"] = officer_name
        extracted["escrow_officer_name"] = officer_name  # Often same person
    
    # Try to find email
    email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", document_text)
    if email_match:
        email = email_match.group(1)
        extracted["title_officer_email"] = email
        extracted["escrow_officer_email"] = email
    
    # Try to find phone
    phone_match = re.search(r"(?:Phone|Tel):?\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", document_text, re.IGNORECASE)
    if phone_match:
        phone = phone_match.group(1).strip()
        extracted["title_officer_phone"] = phone
        extracted["escrow_officer_phone"] = phone
    
    logger.info(f"[FILE_CONTACTS] Extracted {len(extracted)} fields from Title Report")
    
    return extracted


def extract_from_wire_instructions(document_text: str) -> Dict[str, Any]:
    """
    Extract Bank ABA and Account Number from Wire Instructions.
    
    Args:
        document_text: Full text content of Wire Instructions
        
    Returns:
        Dictionary of extracted field values
    """
    extracted = {}
    
    logger.info("[FILE_CONTACTS] Extracting from Wire Instructions...")
    
    # Try to find ABA/Routing number (9 digits)
    aba_match = re.search(r"(?:ABA|Routing|RTN):?\s*(\d{9})", document_text, re.IGNORECASE)
    if aba_match:
        extracted["escrow_bank_aba"] = aba_match.group(1)
    
    # Try to find Account number
    account_match = re.search(r"Account (?:Number|#):?\s*([A-Z0-9-]+)", document_text, re.IGNORECASE)
    if account_match:
        extracted["escrow_bank_account"] = account_match.group(1).strip()
    
    logger.info(f"[FILE_CONTACTS] Extracted {len(extracted)} fields from Wire Instructions")
    
    return extracted


def extract_from_insurance_policy(document_text: str) -> Dict[str, Any]:
    """
    Extract Insurance Company details from Evidence of Insurance (HOI Policy).
    
    Args:
        document_text: Full text content of HOI Policy
        
    Returns:
        Dictionary of extracted field values
    """
    extracted = {}
    
    logger.info("[FILE_CONTACTS] Extracting from Evidence of Insurance...")
    
    # Try to find insurance company name
    company_match = re.search(r"Insurance Company:?\s*([^\n]+)", document_text, re.IGNORECASE)
    if company_match:
        extracted["hazard_ins_company_name"] = company_match.group(1).strip()
    
    # Try to find agent name
    agent_match = re.search(r"Agent:?\s*([^\n]+)", document_text, re.IGNORECASE)
    if agent_match:
        extracted["hazard_ins_agent_name"] = agent_match.group(1).strip()
    
    # Try to find policy number
    policy_match = re.search(r"Policy (?:Number|#):?\s*([A-Z0-9-]+)", document_text, re.IGNORECASE)
    if policy_match:
        extracted["hazard_ins_policy_number"] = policy_match.group(1).strip()
    
    # Try to find email
    email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", document_text)
    if email_match:
        extracted["hazard_ins_agent_email"] = email_match.group(1)
    
    # Try to find phone
    phone_match = re.search(r"(?:Phone|Tel):?\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", document_text, re.IGNORECASE)
    if phone_match:
        extracted["hazard_ins_agent_phone"] = phone_match.group(1).strip()
    
    logger.info(f"[FILE_CONTACTS] Extracted {len(extracted)} fields from Evidence of Insurance")
    
    return extracted


# ============================================================================
# MAIN EXTRACTION FUNCTION
# ============================================================================

def extract_file_contacts(
    documents: List[Dict[str, Any]],
    loan_id: str
) -> Dict[str, Dict[str, Any]]:
    """
    Extract File Contacts information from loan documents.
    
    This function orchestrates extraction from multiple document types and
    combines them into a unified file_contacts dict that will be added to
    field_mappings.
    
    Args:
        documents: List of document dicts with 'title' and 'content'/'text'
        loan_id: The loan GUID (for logging)
        
    Returns:
        Dictionary mapping field IDs to extracted values:
        {
            "field_id": {
                "value": "extracted_value",
                "source": "Document Name",
                "confidence": 0.95
            }
        }
    """
    logger.info(f"[FILE_CONTACTS] Starting File Contacts extraction for loan {loan_id[:8]}...")
    
    file_contacts = {}
    
    # Add fixed lender information
    logger.info("[FILE_CONTACTS] Adding fixed Lender information...")
    for field_name, field_info in FILE_CONTACTS_FIELDS.items():
        if field_name.startswith("lender_") and "value" in field_info:
            file_contacts[field_info["id"]] = {
                "value": field_info["value"],
                "source": "Fixed (SOP)",
                "confidence": 1.0
            }
    
    # Extract from Title Report
    title_doc = None
    for doc in documents:
        title = doc.get("title", "").lower()
        if "title" in title and "report" in title:
            title_doc = doc
            break
    
    if title_doc:
        text = title_doc.get("content") or title_doc.get("text", "")
        if text:
            title_extracted = extract_from_title_report(text)
            for field_name, value in title_extracted.items():
                if field_name in FILE_CONTACTS_FIELDS:
                    field_id = FILE_CONTACTS_FIELDS[field_name]["id"]
                    file_contacts[field_id] = {
                        "value": value,
                        "source": "Title Report",
                        "confidence": 0.8
                    }
        else:
            logger.warning("[FILE_CONTACTS] Title Report found but no content")
    else:
        logger.warning("[FILE_CONTACTS] Title Report not found in documents")
    
    # Extract from Wire Instructions
    wire_doc = None
    for doc in documents:
        title = doc.get("title", "").lower()
        if "wire" in title and "instruction" in title:
            wire_doc = doc
            break
    
    if wire_doc:
        text = wire_doc.get("content") or wire_doc.get("text", "")
        if text:
            wire_extracted = extract_from_wire_instructions(text)
            for field_name, value in wire_extracted.items():
                if field_name in FILE_CONTACTS_FIELDS:
                    field_id = FILE_CONTACTS_FIELDS[field_name]["id"]
                    file_contacts[field_id] = {
                        "value": value,
                        "source": "Wire Instructions",
                        "confidence": 0.9
                    }
    else:
        logger.warning("[FILE_CONTACTS] Wire Instructions not found in documents")
    
    # Extract from Evidence of Insurance
    insurance_doc = None
    for doc in documents:
        title = doc.get("title", "").lower()
        if ("evidence" in title and "insurance" in title) or ("hoi" in title) or ("hazard" in title):
            insurance_doc = doc
            break
    
    if insurance_doc:
        text = insurance_doc.get("content") or insurance_doc.get("text", "")
        if text:
            insurance_extracted = extract_from_insurance_policy(text)
            for field_name, value in insurance_extracted.items():
                if field_name in FILE_CONTACTS_FIELDS:
                    field_id = FILE_CONTACTS_FIELDS[field_name]["id"]
                    file_contacts[field_id] = {
                        "value": value,
                        "source": "Evidence of Insurance",
                        "confidence": 0.8
                    }
    else:
        logger.warning("[FILE_CONTACTS] Evidence of Insurance not found in documents")
    
    logger.info(f"[FILE_CONTACTS] ✅ Extracted {len(file_contacts)} File Contacts fields")
    
    return file_contacts


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_file_contacts_field_ids() -> List[str]:
    """
    Get list of all File Contacts field IDs for reading from Encompass.
    
    Returns:
        List of field IDs
    """
    return [field_info["id"] for field_info in FILE_CONTACTS_FIELDS.values()]


def get_missing_file_contacts(file_contacts: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Identify which File Contacts fields are missing.
    
    Args:
        file_contacts: Dict of extracted file contacts
        
    Returns:
        List of missing field names
    """
    missing = []
    
    for field_name, field_info in FILE_CONTACTS_FIELDS.items():
        field_id = field_info["id"]
        # Skip fixed lender fields (always present)
        if field_name.startswith("lender_"):
            continue
        
        if field_id not in file_contacts or not file_contacts[field_id].get("value"):
            missing.append(field_name)
    
    return missing

