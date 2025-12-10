"""2015 Itemization Validator (G5 - CRITICAL).

Validates mandatory fees and checkboxes for 2015 Itemization disclosure.

Per SOP Video Notes Lines 180-195:
- Bona Fide checkbox must be checked
- Mandatory fees based on loan purpose:
  - All loans: Appraisal, Credit Report
  - Purchase: Title Settlement, Lender Title Insurance, Owner Title Insurance
  - Refinance: Title Settlement, Lender Title Insurance, Recording Fee
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from packages.shared.encompass_client import get_encompass_client

logger = logging.getLogger(__name__)


# Field IDs for itemization
ITEMIZATION_FIELDS = {
    # Checkboxes
    "bona_fide": "NEWHUD.X1067",  # Bona Fide checkbox
    "itemize_when_printing": "UNKNOWN",  # TODO: Find field ID
    
    # Fees
    "appraisal_fee": "641",  # Appraisal Fee
    "credit_report": "581",  # Credit Report Fee
    "title_settlement": "390",  # Title Settlement Fee
    "lender_title": "587",  # Lender Title Insurance
    "owner_title": "UNKNOWN",  # TODO: Find field ID
    "recording_fee": "UNKNOWN",  # TODO: Find field ID
}


@dataclass
class ItemizationResult:
    """Result from itemization validation."""
    all_valid: bool
    loan_purpose: str
    checkboxes_checked: List[str]
    checkboxes_missing: List[str]
    fees_present: List[str]
    fees_missing: List[str]
    warnings: List[str]


def validate_itemization(loan_id: str, loan_purpose: str = "Purchase") -> ItemizationResult:
    """Validate 2015 Itemization requirements.
    
    Args:
        loan_id: Encompass loan GUID
        loan_purpose: Loan purpose (Purchase/Refinance)
        
    Returns:
        ItemizationResult with validation details
    """
    logger.info(f"[G5] Validating itemization for {loan_purpose} loan {loan_id[:8]}...")
    
    # Log warnings for unknown field IDs
    logger.warning("[G5] 'Itemize fees when printing' checkbox field ID UNKNOWN - requires manual verification")
    logger.warning("[G5] Owner Title Insurance fee field ID UNKNOWN - requires manual verification")
    logger.warning("[G5] Recording Fee field ID UNKNOWN - requires manual verification")
    
    checkboxes_checked = []
    checkboxes_missing = []
    fees_present = []
    fees_missing = []
    warnings = []
    
    try:
        client = get_encompass_client()
        
        # Get known fields
        fields_to_check = [
            ITEMIZATION_FIELDS["bona_fide"],
            ITEMIZATION_FIELDS["appraisal_fee"],
            ITEMIZATION_FIELDS["credit_report"],
            ITEMIZATION_FIELDS["title_settlement"],
            ITEMIZATION_FIELDS["lender_title"],
        ]
        
        loan_data = client.get_loan_fields(loan_id, fields_to_check)
        
        # Check Bona Fide checkbox
        bona_fide = loan_data.get(ITEMIZATION_FIELDS["bona_fide"])
        if bona_fide:
            checkboxes_checked.append("Bona Fide")
        else:
            checkboxes_missing.append("Bona Fide")
            warnings.append("Bona Fide checkbox not checked")
        
        # Check mandatory fees (all loans)
        appraisal = loan_data.get(ITEMIZATION_FIELDS["appraisal_fee"])
        if appraisal:
            fees_present.append("Appraisal Fee")
        else:
            fees_missing.append("Appraisal Fee")
            warnings.append("Appraisal Fee missing")
        
        credit = loan_data.get(ITEMIZATION_FIELDS["credit_report"])
        if credit:
            fees_present.append("Credit Report")
        else:
            fees_missing.append("Credit Report")
            warnings.append("Credit Report Fee missing")
        
        # Check purpose-specific fees
        title_settlement = loan_data.get(ITEMIZATION_FIELDS["title_settlement"])
        lender_title = loan_data.get(ITEMIZATION_FIELDS["lender_title"])
        
        if title_settlement:
            fees_present.append("Title Settlement")
        else:
            fees_missing.append("Title Settlement")
            warnings.append("Title Settlement Fee missing")
        
        if lender_title:
            fees_present.append("Lender Title Insurance")
        else:
            fees_missing.append("Lender Title Insurance")
            warnings.append("Lender Title Insurance missing")
        
        if loan_purpose == "Purchase":
            # Owner Title Insurance - field ID unknown
            fees_missing.append("Owner Title Insurance (field ID UNKNOWN)")
            warnings.append("Owner Title Insurance field ID UNKNOWN - manual verification required")
        
        if loan_purpose == "Refinance" or loan_purpose == "NoCash-Out Refinance" or loan_purpose == "Cash-Out Refinance":
            # Recording Fee - field ID unknown
            fees_missing.append("Recording Fee (field ID UNKNOWN)")
            warnings.append("Recording Fee field ID UNKNOWN - manual verification required")
        
        # Add warning for itemize when printing checkbox
        checkboxes_missing.append("Itemize fees when printing (field ID UNKNOWN)")
        warnings.append("'Itemize fees when printing' checkbox field ID UNKNOWN - manual verification required")
        
        all_valid = len(checkboxes_missing) == 0 and len(fees_missing) == 0
        
        logger.info(f"[G5] Checkboxes checked: {len(checkboxes_checked)}, missing: {len(checkboxes_missing)}")
        logger.info(f"[G5] Fees present: {len(fees_present)}, missing: {len(fees_missing)}")
        
        return ItemizationResult(
            all_valid=all_valid,
            loan_purpose=loan_purpose,
            checkboxes_checked=checkboxes_checked,
            checkboxes_missing=checkboxes_missing,
            fees_present=fees_present,
            fees_missing=fees_missing,
            warnings=warnings,
        )
        
    except Exception as e:
        logger.error(f"[G5] Error validating itemization: {e}")
        return ItemizationResult(
            all_valid=False,
            loan_purpose=loan_purpose,
            checkboxes_checked=[],
            checkboxes_missing=["Error occurred"],
            fees_present=[],
            fees_missing=["Error occurred"],
            warnings=[f"Validation error: {str(e)}"],
        )
