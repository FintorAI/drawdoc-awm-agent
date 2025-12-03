"""Shared Encompass field I/O utilities for disclosure and draw docs agents.

This module provides high-level functions for reading and writing Encompass fields,
as well as utility functions for getting loan metadata.
"""

import os
import logging
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .auth import get_access_token

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD I/O FUNCTIONS
# =============================================================================

def read_fields(loan_id: str, field_ids: List[str]) -> Dict[str, Any]:
    """Read multiple field values from Encompass using Field Reader API.
    
    This function uses the Encompass Field Reader endpoint which is more
    permissive and designed for bulk field reads.
    
    Args:
        loan_id: Encompass loan GUID
        field_ids: List of Encompass field IDs to retrieve
        
    Returns:
        Dictionary mapping field_id to value (None if not found or empty)
        
    Example:
        values = read_fields(loan_id, ["4000", "4002", "1109"])
        borrower_name = values.get("4000")
    """
    if not field_ids:
        return {}
    
    # Deduplicate field IDs to avoid API errors
    original_count = len(field_ids)
    field_ids = list(set(field_ids))
    if len(field_ids) < original_count:
        logger.warning(f"[READ] Removed {original_count - len(field_ids)} duplicate field IDs")
    
    # Get OAuth2 token
    access_token = get_access_token()
    
    # Build API request
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/fieldReader"
    
    logger.info(f"[READ] Reading {len(field_ids)} fields for loan {loan_id[:8]}...")
    logger.info(f"[READ] API Base URL: {api_base_url}")
    logger.info(f"[READ] Endpoint: POST /encompass/v3/loans/{loan_id[:8]}...{loan_id[-8:]}/fieldReader")
    logger.info(f"[READ] Token: {access_token[:10]}...{access_token[-6:]}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "invalidFieldBehavior": "Exclude"  # Exclude invalid fields from response
    }
    
    try:
        # POST to Field Reader endpoint with field IDs in body
        response = requests.post(
            url,
            json=field_ids,
            headers=headers,
            params=params,
            timeout=60
        )
        
        response.raise_for_status()
        
        # Field Reader returns: { "field_id": "value", ... }
        result = response.json()
        
        # Normalize: convert empty strings to None
        normalized = {}
        for field_id in field_ids:
            value = result.get(field_id)
            if value is not None and str(value).strip() != "":
                normalized[field_id] = value
            else:
                normalized[field_id] = None
        
        logger.debug(f"[READ] Retrieved {sum(1 for v in normalized.values() if v is not None)} values")
        return normalized
        
    except requests.HTTPError as e:
        error_msg = f"Field read failed (status {e.response.status_code}): {e.response.text}"
        logger.error(f"[READ] {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as e:
        logger.error(f"[READ] Error reading fields: {e}")
        raise


def read_field(loan_id: str, field_id: str) -> Optional[Any]:
    """Read a single field value from Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID to retrieve
        
    Returns:
        Field value, or None if not found or empty
    """
    result = read_fields(loan_id, [field_id])
    return result.get(field_id)


def write_fields(loan_id: str, updates: Dict[str, Any], dry_run: bool = True) -> bool:
    """Write multiple field values to Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        updates: Dictionary mapping field_id to new value
        dry_run: If True, only simulate the write (default: True for safety)
        
    Returns:
        True if all writes succeeded, False otherwise
        
    Example:
        success = write_fields(loan_id, {
            "4000": "John",
            "4002": "Doe"
        }, dry_run=False)
    """
    if not updates:
        return True
    
    if dry_run:
        logger.info(f"[WRITE] [DRY RUN] Would write {len(updates)} fields to loan {loan_id[:8]}")
        for field_id, value in updates.items():
            logger.debug(f"[WRITE] [DRY RUN] {field_id} = {value}")
        return True
    
    logger.info(f"[WRITE] Writing {len(updates)} fields to loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    try:
        # Write each field
        all_success = True
        for field_id, value in updates.items():
            try:
                success = encompass.write_field(loan_id, field_id, value)
                if success:
                    logger.debug(f"[WRITE] Successfully wrote {field_id} = {value}")
                else:
                    logger.error(f"[WRITE] Failed to write {field_id}")
                    all_success = False
            except Exception as e:
                logger.error(f"[WRITE] Error writing {field_id}: {e}")
                all_success = False
        
        return all_success
        
    except Exception as e:
        logger.error(f"[WRITE] Error writing fields: {e}")
        return False


def write_field(loan_id: str, field_id: str, value: Any, dry_run: bool = True) -> bool:
    """Write a single field value to Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID to write
        value: New value for the field
        dry_run: If True, only simulate the write (default: True for safety)
        
    Returns:
        True if write succeeded, False otherwise
    """
    return write_fields(loan_id, {field_id: value}, dry_run=dry_run)


# =============================================================================
# LOAN METADATA FUNCTIONS
# =============================================================================

# Encompass field IDs for loan metadata
LOAN_TYPE_FIELD = "1172"  # Loan Type (Conventional, FHA, VA, USDA)
LOAN_PURPOSE_FIELD = "19"  # Loan Purpose (Purchase, Refinance, etc.)
LOAN_AMOUNT_FIELD = "1109"  # Loan Amount
APPRAISED_VALUE_FIELD = "356"  # Appraised Value
PURCHASE_PRICE_FIELD = "136"  # Purchase Price
PROPERTY_TYPE_FIELD = "1041"  # Property Type
OCCUPANCY_TYPE_FIELD = "1811"  # Occupancy Type
PROPERTY_STATE_FIELD = "14"  # Property State
LTV_FIELD = "353"  # LTV
CLTV_FIELD = "976"  # CLTV
INTEREST_RATE_FIELD = "3"  # Note Rate
LOAN_TERM_FIELD = "4"  # Loan Term (months)


def get_loan_type(loan_id: str) -> str:
    """Get the loan type for a loan.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Loan type string: "Conventional", "FHA", "VA", "USDA", or "Unknown"
    """
    value = read_field(loan_id, LOAN_TYPE_FIELD)
    
    if value is None:
        return "Unknown"
    
    value_str = str(value).strip().lower()
    
    if "conventional" in value_str or "conv" in value_str:
        return "Conventional"
    elif "fha" in value_str:
        return "FHA"
    elif "va" in value_str:
        return "VA"
    elif "usda" in value_str or "rural" in value_str:
        return "USDA"
    else:
        return value_str.title() if value_str else "Unknown"


def get_loan_purpose(loan_id: str) -> str:
    """Get the loan purpose for a loan.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Loan purpose string: "Purchase", "Refinance", "CashOut", or "Unknown"
    """
    value = read_field(loan_id, LOAN_PURPOSE_FIELD)
    
    if value is None:
        return "Unknown"
    
    value_str = str(value).strip().lower()
    
    if "purchase" in value_str:
        return "Purchase"
    elif "refinance" in value_str or "refi" in value_str:
        if "cash" in value_str:
            return "CashOut"
        return "Refinance"
    elif "construction" in value_str:
        return "Construction"
    else:
        return value_str.title() if value_str else "Unknown"


def get_loan_summary(loan_id: str) -> Dict[str, Any]:
    """Get a summary of key loan information.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with key loan attributes:
        - loan_type: Conventional, FHA, VA, USDA
        - loan_purpose: Purchase, Refinance, CashOut
        - loan_amount: Loan amount
        - appraised_value: Appraised value
        - purchase_price: Purchase price (if purchase)
        - ltv: LTV percentage
        - cltv: CLTV percentage
        - interest_rate: Note rate
        - loan_term: Term in months
        - property_state: State abbreviation
        - property_type: Property type
        - occupancy_type: Occupancy type
    """
    field_ids = [
        LOAN_TYPE_FIELD,
        LOAN_PURPOSE_FIELD,
        LOAN_AMOUNT_FIELD,
        APPRAISED_VALUE_FIELD,
        PURCHASE_PRICE_FIELD,
        LTV_FIELD,
        CLTV_FIELD,
        INTEREST_RATE_FIELD,
        LOAN_TERM_FIELD,
        PROPERTY_STATE_FIELD,
        PROPERTY_TYPE_FIELD,
        OCCUPANCY_TYPE_FIELD,
    ]
    
    values = read_fields(loan_id, field_ids)
    
    # Parse numeric values
    def parse_float(val):
        if val is None:
            return None
        try:
            return float(str(val).replace(",", "").replace("$", "").replace("%", ""))
        except:
            return None
    
    def parse_int(val):
        if val is None:
            return None
        try:
            return int(float(str(val).replace(",", "")))
        except:
            return None
    
    return {
        "loan_id": loan_id,
        "loan_type": get_loan_type(loan_id),
        "loan_purpose": get_loan_purpose(loan_id),
        "loan_amount": parse_float(values.get(LOAN_AMOUNT_FIELD)),
        "appraised_value": parse_float(values.get(APPRAISED_VALUE_FIELD)),
        "purchase_price": parse_float(values.get(PURCHASE_PRICE_FIELD)),
        "ltv": parse_float(values.get(LTV_FIELD)),
        "cltv": parse_float(values.get(CLTV_FIELD)),
        "interest_rate": parse_float(values.get(INTEREST_RATE_FIELD)),
        "loan_term": parse_int(values.get(LOAN_TERM_FIELD)),
        "property_state": values.get(PROPERTY_STATE_FIELD),
        "property_type": values.get(PROPERTY_TYPE_FIELD),
        "occupancy_type": values.get(OCCUPANCY_TYPE_FIELD),
    }


def is_conventional_loan(loan_id: str) -> bool:
    """Check if a loan is Conventional type.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        True if Conventional, False otherwise
    """
    return get_loan_type(loan_id) == "Conventional"


def is_government_loan(loan_id: str) -> bool:
    """Check if a loan is a government loan (FHA, VA, or USDA).
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        True if FHA, VA, or USDA, False otherwise
    """
    loan_type = get_loan_type(loan_id)
    return loan_type in ["FHA", "VA", "USDA"]

