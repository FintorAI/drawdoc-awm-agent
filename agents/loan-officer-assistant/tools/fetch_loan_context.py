"""
Loan Officer Assistant - Fetch Loan Context Tool

Retrieves loan data from Encompass and normalizes it into LoanFacts dataclass.
This tool leverages the existing Encompass API utilities from the packages/shared module.

Usage:
    loan_facts = await fetch_loan_context("loan-guid-here")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add paths for imports
LOA_DIR = Path(__file__).parent.parent
PROJECT_ROOT = LOA_DIR.parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Import shared utilities - reuse existing auth and API functions
from packages.shared import get_access_token, read_fields

from state import (
    BorrowerFacts,
    EFolderDoc,
    LoanFacts,
    MilestoneInfo,
    PropertyFacts,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_DIR = Path(__file__).parent.parent / "config"
FIELD_MAPPING_PATH = CONFIG_DIR / "field_mapping.yaml"


def load_field_mapping() -> Dict[str, Any]:
    """Load field mapping configuration from YAML."""
    if not FIELD_MAPPING_PATH.exists():
        logger.warning(f"Field mapping not found at {FIELD_MAPPING_PATH}")
        return {}
    
    with open(FIELD_MAPPING_PATH, "r") as f:
        return yaml.safe_load(f)


# =============================================================================
# ENCOMPASS API FUNCTIONS
# =============================================================================
# These functions wrap the existing fetch_loan_info.py capabilities
# but use the shared auth module for consistency

def _get_api_client():
    """Get authenticated API client components."""
    import os
    from dotenv import load_dotenv
    
    # Load environment
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(env_path)
    
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    access_token = get_access_token()
    
    return api_base_url, access_token


def _fetch_milestones(loan_id: str) -> List[Dict]:
    """
    Fetch loan milestones from Encompass.
    
    Replicates fetch_milestones from fetch_loan_info.py but uses shared auth.
    """
    import requests
    
    api_base_url, token = _get_api_client()
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/milestones"
    
    logger.info(f"[MILESTONES] Fetching milestones for loan {loan_id[:8]}...")
    
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        if resp.status_code != 200:
            logger.warning(f"[MILESTONES] Request failed: {resp.status_code}")
            return []
        
        milestones = resp.json()
        logger.info(f"[MILESTONES] ✓ Found {len(milestones)} milestones")
        return milestones
        
    except Exception as e:
        logger.error(f"[MILESTONES] Error: {e}")
        return []


def _fetch_attachments(loan_id: str) -> List[Dict]:
    """
    Fetch eFolder attachments from Encompass.
    
    Replicates fetch_loan_documents from fetch_loan_info.py but uses shared auth.
    """
    import requests
    
    api_base_url, token = _get_api_client()
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/attachments"
    
    logger.info(f"[ATTACHMENTS] Fetching documents for loan {loan_id[:8]}...")
    
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        if resp.status_code != 200:
            logger.warning(f"[ATTACHMENTS] Request failed: {resp.status_code}")
            return []
        
        documents = resp.json()
        logger.info(f"[ATTACHMENTS] ✓ Found {len(documents)} documents")
        return documents
        
    except Exception as e:
        logger.error(f"[ATTACHMENTS] Error: {e}")
        return []


# =============================================================================
# FIELD IDS TO FETCH
# =============================================================================
# Comprehensive list of Encompass field IDs needed for LoanFacts
# Based on field_mapping.yaml and the architecture spec

FIELD_IDS = [
    # Loan Identification
    "364",    # Loan Number
    "1172",   # Loan Type
    "1401",   # Loan Program
    "19",     # Loan Purpose
    "608",    # Amortization Type
    
    # Primary Borrower
    "4000",   # First Name
    "4001",   # Middle Name
    "4002",   # Last Name
    "4003",   # Suffix
    "65",     # SSN
    "52",     # DOB
    "1268",   # Email
    "66",     # Home Phone
    "1490",   # Cell Phone
    "84",     # Work Phone
    "471",    # Marital Status
    "1523",   # Citizenship Status
    "1199",   # Dependents Count
    
    # Borrower Address
    "FR0104", # Current Street
    "FR0106", # Current City
    "FR0107", # Current State
    "FR0108", # Current Zip
    "1402",   # Years at Current Address
    
    # Borrower Employment
    "BE0015", # Employer Name
    "BE0003", # Job Title
    "BE0016", # Employer Street
    "BE0018", # Employer City
    "BE0019", # Employer State
    "BE0020", # Employer Zip
    "BE0012", # Employer Phone
    "BE0002", # Self Employed
    "BE0005", # Years on Job
    "BE0006", # Months on Job
    "1756",   # Years in Profession
    
    # Borrower Income
    "1",      # Base Income
    "1048",   # Overtime
    "1049",   # Bonus
    "1050",   # Commission
    "1051",   # Dividends/Interest
    "1052",   # Net Rental Income
    "1053",   # Other Income
    "1759",   # Total Monthly Income
    
    # Co-Borrower
    "4004",   # First Name
    "4005",   # Middle Name
    "4006",   # Last Name
    "4007",   # Suffix
    "68",     # SSN
    "1496",   # DOB
    "1519",   # Email
    "97",     # Home Phone
    "1520",   # Cell Phone
    "98",     # Work Phone
    "CE0015", # Employer Name
    "CE0003", # Job Title
    
    # Property
    "11",     # Address
    "12",     # City
    "14",     # State
    "15",     # Zip
    "13",     # County
    "1041",   # Property Type
    "1811",   # Occupancy Type
    "16",     # Number of Units
    "18",     # Year Built
    "1396",   # Legal Description
    "1397",   # APN
    "1981",   # Manufactured Home
    "1026",   # Condo Project Type
    "696",    # Has HOA
    "232",    # Monthly HOA Dues
    
    # Loan Amounts
    "1109",   # Loan Amount
    "136",    # Purchase Price
    "356",    # Appraised Value
    "353",    # LTV
    "976",    # CLTV
    "3",      # Interest Rate
    "4",      # Loan Term
    "337",    # Cash to Close
    "1335",   # Down Payment
    "1771",   # Down Payment %
    "740",    # Front DTI
    "742",    # Back DTI
    
    # Dates
    "745",    # Application Date
    "682",    # Estimated Closing Date
    "762",    # Lock Date
    "763",    # Lock Expiration Date
    
    # Loan Officer
    "317",    # LO Name
    "88",     # LO Email
    "362",    # LO NMLS
    "318",    # Processor Name
    
    # Credit
    "1056",   # Credit Score
    "1057",   # Credit Score Date
]


# =============================================================================
# DATA NORMALIZATION
# =============================================================================

def _parse_float(value: Any) -> Optional[float]:
    """Safely parse a value to float."""
    if value is None or value == "":
        return None
    try:
        # Handle string values with formatting
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").replace("%", "")
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_int(value: Any) -> Optional[int]:
    """Safely parse a value to int."""
    parsed = _parse_float(value)
    return int(parsed) if parsed is not None else None


def _parse_bool(value: Any) -> Optional[bool]:
    """Safely parse a value to boolean."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "y", "1")
    return bool(value)


def _is_populated(value: Any) -> bool:
    """Check if a value is populated (not None or empty)."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _normalize_borrower(fields: Dict[str, Any], prefix: str, borrower_type: str) -> Optional[BorrowerFacts]:
    """
    Normalize borrower data from Encompass fields.
    
    Args:
        fields: Raw field values from Encompass
        prefix: Field prefix ("" for primary, "4004" series for co-borrower)
        borrower_type: "PRIMARY" or "CO_BORROWER"
    """
    # Field mappings for primary vs co-borrower
    if borrower_type == "PRIMARY":
        mapping = {
            "first_name": "4000",
            "middle_name": "4001",
            "last_name": "4002",
            "suffix": "4003",
            "ssn": "65",
            "dob": "52",
            "email": "1268",
            "phone": "66",
            "cell_phone": "1490",
            "work_phone": "84",
            "marital_status": "471",
            "citizenship_status": "1523",
            "dependents_count": "1199",
            "current_address_street": "FR0104",
            "current_address_city": "FR0106",
            "current_address_state": "FR0107",
            "current_address_zip": "FR0108",
            "years_at_current_address": "1402",
            "employer_name": "BE0015",
            "job_title": "BE0003",
            "employer_address_street": "BE0016",
            "employer_address_city": "BE0018",
            "employer_address_state": "BE0019",
            "employer_address_zip": "BE0020",
            "employer_phone": "BE0012",
            "is_self_employed": "BE0002",
            "years_on_job": "BE0005",
            "months_on_job": "BE0006",
            "years_in_profession": "1756",
            "base_income": "1",
            "overtime_income": "1048",
            "bonus_income": "1049",
            "commission_income": "1050",
            "dividends_income": "1051",
            "rental_income": "1052",
            "other_income": "1053",
            "total_monthly_income": "1759",
        }
    else:  # CO_BORROWER
        mapping = {
            "first_name": "4004",
            "middle_name": "4005",
            "last_name": "4006",
            "suffix": "4007",
            "ssn": "68",
            "dob": "1496",
            "email": "1519",
            "phone": "97",
            "cell_phone": "1520",
            "work_phone": "98",
            "employer_name": "CE0015",
            "job_title": "CE0003",
        }
    
    # Check if this borrower exists (has at least first or last name)
    first_name_field = mapping.get("first_name", "")
    last_name_field = mapping.get("last_name", "")
    
    first_name = fields.get(first_name_field)
    last_name = fields.get(last_name_field)
    
    if not _is_populated(first_name) and not _is_populated(last_name):
        return None
    
    borrower = BorrowerFacts(borrower_type=borrower_type)
    
    # Map all available fields
    for attr, field_id in mapping.items():
        value = fields.get(field_id)
        if _is_populated(value):
            # Type conversion based on attribute
            if attr in ("dependents_count", "months_on_job"):
                value = _parse_int(value)
            elif attr in ("years_at_current_address", "years_on_job", "years_in_profession",
                          "base_income", "overtime_income", "bonus_income", "commission_income",
                          "dividends_income", "rental_income", "other_income", "total_monthly_income"):
                value = _parse_float(value)
            elif attr == "is_self_employed":
                value = _parse_bool(value)
            
            setattr(borrower, attr, value)
    
    return borrower


def _normalize_property(fields: Dict[str, Any]) -> PropertyFacts:
    """Normalize property data from Encompass fields."""
    prop = PropertyFacts()
    
    mapping = {
        "address": "11",
        "city": "12",
        "state": "14",
        "zip": "15",
        "county": "13",
        "property_type": "1041",
        "occupancy_type": "1811",
        "number_of_units": "16",
        "year_built": "18",
        "legal_description": "1396",
        "apn": "1397",
        "is_manufactured": "1981",
        "condo_project_type": "1026",
        "has_hoa": "696",
        "monthly_hoa_dues": "232",
    }
    
    for attr, field_id in mapping.items():
        value = fields.get(field_id)
        if _is_populated(value):
            if attr in ("number_of_units", "year_built"):
                value = _parse_int(value)
            elif attr == "monthly_hoa_dues":
                value = _parse_float(value)
            elif attr in ("is_manufactured", "has_hoa"):
                value = _parse_bool(value)
            
            setattr(prop, attr, value)
    
    # Derive is_condo from property_type
    if prop.property_type:
        prop.is_condo = "condo" in prop.property_type.lower()
    
    return prop


def _normalize_milestones(raw_milestones: List[Dict]) -> List[MilestoneInfo]:
    """Normalize milestone data from v3 API."""
    milestones = []
    
    for ms in raw_milestones:
        # v3 API uses "name", v1 used "milestoneName" - support both for compatibility
        milestone_name = ms.get("name") or ms.get("milestoneName", "Unknown")
        milestone = MilestoneInfo(
            name=milestone_name,
            status="Completed" if ms.get("doneIndicator") else "Pending",
            status_date=ms.get("startDate"),
        )
        milestones.append(milestone)
    
    return milestones


def _normalize_efolder_docs(raw_docs: List[Dict]) -> List[EFolderDoc]:
    """Normalize eFolder document data."""
    docs = []
    
    for doc in raw_docs:
        if doc.get("isRemoved", False):
            continue
            
        efolder_doc = EFolderDoc(
            attachment_id=doc.get("id", ""),
            title=doc.get("title", "Unknown"),
            date_created=doc.get("createdDate"),
            date_modified=doc.get("lastModifiedDate"),
            is_active=not doc.get("isRemoved", False),
        )
        docs.append(efolder_doc)
    
    return docs


def _compute_scenario_tag(loan_facts: LoanFacts) -> str:
    """
    Compute scenario tag for rule routing.
    
    Format: {LOAN_TYPE}_{PURPOSE}_{OCCUPANCY}
    Example: CONV_PURCHASE_PRIMARY
    """
    parts = []
    
    # Loan type
    loan_type = (loan_facts.loan_type or "").upper()
    if "CONVENTIONAL" in loan_type or "CONV" in loan_type:
        parts.append("CONV")
    elif "FHA" in loan_type:
        parts.append("FHA")
    elif "VA" in loan_type:
        parts.append("VA")
    elif "USDA" in loan_type:
        parts.append("USDA")
    else:
        parts.append("OTHER")
    
    # Loan purpose
    purpose = (loan_facts.loan_purpose or "").upper()
    if "PURCHASE" in purpose:
        parts.append("PURCHASE")
    elif "REFINANCE" in purpose or "REFI" in purpose:
        parts.append("REFI")
    elif "CASH" in purpose:
        parts.append("CASHOUT")
    else:
        parts.append("OTHER")
    
    # Occupancy
    occupancy = ""
    if loan_facts.subject_property:
        occupancy = (loan_facts.subject_property.occupancy_type or "").upper()
    
    if "PRIMARY" in occupancy:
        parts.append("PRIMARY")
    elif "SECOND" in occupancy:
        parts.append("SECOND")
    elif "INVESTMENT" in occupancy or "INVESTOR" in occupancy:
        parts.append("INVESTMENT")
    else:
        parts.append("PRIMARY")  # Default
    
    return "_".join(parts)


def _is_mvp_supported(loan_facts: LoanFacts) -> bool:
    """
    Check if loan is within MVP scope.
    
    MVP supports: Conventional purchase/refi loans
    """
    loan_type = (loan_facts.loan_type or "").upper()
    
    # MVP: Conventional only
    if "FHA" in loan_type or "VA" in loan_type or "USDA" in loan_type:
        return False
    
    return True


# =============================================================================
# MAIN FETCH FUNCTION
# =============================================================================

async def fetch_loan_context(loan_id: str) -> LoanFacts:
    """
    Fetch loan context from Encompass and normalize to LoanFacts.
    
    This is the primary entry point for retrieving loan data.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        LoanFacts: Normalized loan data ready for gap analysis
        
    Raises:
        RuntimeError: If unable to retrieve loan data
    """
    logger.info(f"[FETCH] Starting loan context fetch for {loan_id[:8]}...")
    
    # 1. Fetch fields using shared read_fields utility
    logger.info(f"[FETCH] Fetching {len(FIELD_IDS)} fields...")
    fields = read_fields(loan_id, FIELD_IDS, context="[LOA]")
    
    if not fields:
        raise RuntimeError(f"Failed to retrieve fields for loan {loan_id}")
    
    # 2. Fetch milestones
    milestones_raw = _fetch_milestones(loan_id)
    
    # 3. Fetch eFolder attachments
    attachments_raw = _fetch_attachments(loan_id)
    
    # 4. Build LoanFacts
    loan_facts = LoanFacts(loan_id=loan_id)
    loan_facts.fetch_timestamp = datetime.utcnow().isoformat()
    
    # Basic loan fields
    loan_facts.loan_number = fields.get("364")
    loan_facts.loan_type = fields.get("1172")
    loan_facts.loan_program = fields.get("1401")
    loan_facts.loan_purpose = fields.get("19")
    loan_facts.amortization_type = fields.get("608")
    
    # Loan amounts
    loan_facts.loan_amount = _parse_float(fields.get("1109"))
    loan_facts.purchase_price = _parse_float(fields.get("136"))
    loan_facts.appraised_value = _parse_float(fields.get("356"))
    loan_facts.ltv = _parse_float(fields.get("353"))
    loan_facts.cltv = _parse_float(fields.get("976"))
    loan_facts.interest_rate = _parse_float(fields.get("3"))
    loan_facts.loan_term_months = _parse_int(fields.get("4"))
    loan_facts.down_payment = _parse_float(fields.get("1335"))
    loan_facts.down_payment_percent = _parse_float(fields.get("1771"))
    loan_facts.cash_to_close = _parse_float(fields.get("337"))
    loan_facts.dti_front = _parse_float(fields.get("740"))
    loan_facts.dti_back = _parse_float(fields.get("742"))
    
    # Dates
    loan_facts.application_date = fields.get("745")
    loan_facts.estimated_closing_date = fields.get("682")
    loan_facts.lock_date = fields.get("762")
    loan_facts.lock_expiration_date = fields.get("763")
    
    # Loan Officer
    loan_facts.lo_name = fields.get("317")
    loan_facts.lo_email = fields.get("88")
    loan_facts.lo_nmls = fields.get("362")
    loan_facts.processor_name = fields.get("318")
    
    # Credit
    loan_facts.credit_score = _parse_int(fields.get("1056"))
    loan_facts.credit_score_date = fields.get("1057")
    
    # Normalize borrowers
    primary_borrower = _normalize_borrower(fields, "", "PRIMARY")
    if primary_borrower:
        loan_facts.borrowers.append(primary_borrower)
    
    co_borrower = _normalize_borrower(fields, "", "CO_BORROWER")
    if co_borrower:
        loan_facts.borrowers.append(co_borrower)
    
    # Normalize property
    loan_facts.subject_property = _normalize_property(fields)
    
    # Normalize milestones
    loan_facts.milestones = _normalize_milestones(milestones_raw)
    
    # Find current milestone (first incomplete one)
    for ms in loan_facts.milestones:
        if ms.status != "Completed":
            loan_facts.current_milestone = ms.name
            break
    else:
        # All complete, use last one
        if loan_facts.milestones:
            loan_facts.current_milestone = loan_facts.milestones[-1].name
    
    # Normalize eFolder docs
    loan_facts.efolder_docs = _normalize_efolder_docs(attachments_raw)
    
    # Compute derived fields
    loan_facts.scenario_tag = _compute_scenario_tag(loan_facts)
    loan_facts.is_mvp_supported = _is_mvp_supported(loan_facts)
    
    logger.info(f"[FETCH] ✓ Loan context complete: {loan_facts.scenario_tag}")
    logger.info(f"[FETCH]   - Borrowers: {len(loan_facts.borrowers)}")
    logger.info(f"[FETCH]   - Milestones: {len(loan_facts.milestones)}")
    logger.info(f"[FETCH]   - Documents: {len(loan_facts.efolder_docs)}")
    logger.info(f"[FETCH]   - MVP Supported: {loan_facts.is_mvp_supported}")
    
    return loan_facts


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================

def fetch_loan_context_sync(loan_id: str) -> LoanFacts:
    """
    Synchronous wrapper for fetch_loan_context.
    
    Use this for non-async contexts or testing.
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Create a new loop for nested call
        import nest_asyncio
        nest_asyncio.apply()
    
    return asyncio.run(fetch_loan_context(loan_id))


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import json
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python fetch_loan_context.py <loan_id>")
        print("Example: python fetch_loan_context.py 59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    try:
        loan_facts = fetch_loan_context_sync(loan_id)
        print("\n" + "=" * 60)
        print("LOAN FACTS")
        print("=" * 60)
        print(json.dumps(loan_facts.to_dict(), indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

