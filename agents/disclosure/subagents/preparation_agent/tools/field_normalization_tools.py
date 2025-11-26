"""Field normalization tools for disclosure preparation agent.

These tools clean and normalize field values to standard formats.
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to (XXX) XXX-XXXX format.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        Normalized phone number in (XXX) XXX-XXXX format
        
    Example:
        "5551234567" -> "(555) 123-4567"
        "555-123-4567" -> "(555) 123-4567"
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
    # Check if we have 10 digits
    if len(digits) == 10:
        normalized = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        logger.debug(f"[NORMALIZE] Phone: {phone} -> {normalized}")
        return normalized
    elif len(digits) == 11 and digits[0] == '1':
        # Handle numbers starting with 1
        normalized = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        logger.debug(f"[NORMALIZE] Phone: {phone} -> {normalized}")
        return normalized
    
    # Return original if can't normalize
    logger.warning(f"[NORMALIZE] Could not normalize phone: {phone}")
    return phone


@tool
def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format.
    
    Tries multiple common date formats and converts to standardized format.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date in YYYY-MM-DD format
        
    Example:
        "12/25/2023" -> "2023-12-25"
        "Dec 25, 2023" -> "2023-12-25"
    """
    if not date_str:
        return date_str
    
    # Try multiple date formats
    formats = [
        "%m/%d/%Y",     # 12/25/2023
        "%Y-%m-%d",     # 2023-12-25 (already correct)
        "%m-%d-%Y",     # 12-25-2023
        "%d/%m/%Y",     # 25/12/2023
        "%B %d, %Y",    # December 25, 2023
        "%b %d, %Y",    # Dec 25, 2023
        "%Y/%m/%d",     # 2023/12/25
        "%m/%d/%y",     # 12/25/23
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(str(date_str).strip(), fmt)
            normalized = dt.strftime("%Y-%m-%d")
            logger.debug(f"[NORMALIZE] Date: {date_str} -> {normalized}")
            return normalized
        except:
            continue
    
    # Return original if can't parse
    logger.warning(f"[NORMALIZE] Could not normalize date: {date_str}")
    return date_str


@tool
def normalize_ssn(ssn: str) -> str:
    """Normalize SSN to XXX-XX-XXXX format.
    
    Args:
        ssn: SSN in any format
        
    Returns:
        SSN in XXX-XX-XXXX format
        
    Example:
        "123456789" -> "123-45-6789"
    """
    if not ssn:
        return ssn
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(ssn))
    
    # Check if we have 9 digits
    if len(digits) == 9:
        normalized = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        logger.debug(f"[NORMALIZE] SSN: ***-**-{digits[5:]} -> ***-**-{digits[5:]}")
        return normalized
    
    # Return original if can't normalize
    logger.warning(f"[NORMALIZE] Could not normalize SSN (wrong length)")
    return ssn


@tool
def normalize_currency(amount: Any) -> str:
    """Normalize currency amount to standard decimal format.
    
    Args:
        amount: Currency amount in various formats
        
    Returns:
        Amount as decimal string (e.g., "150000.00")
        
    Example:
        "$150,000" -> "150000.00"
        "150000" -> "150000.00"
    """
    if not amount:
        return amount
    
    # Convert to string and remove currency symbols and commas
    amount_str = str(amount).replace('$', '').replace(',', '').strip()
    
    try:
        # Convert to float and format with 2 decimal places
        amount_float = float(amount_str)
        normalized = f"{amount_float:.2f}"
        logger.debug(f"[NORMALIZE] Currency: {amount} -> {normalized}")
        return normalized
    except:
        logger.warning(f"[NORMALIZE] Could not normalize currency: {amount}")
        return str(amount)


@tool
def clean_field_value(field_id: str, value: Any, field_type: str) -> Any:
    """Clean and normalize a field value based on its type.
    
    This is a smart function that applies the right normalization based on field type.
    
    Args:
        field_id: Encompass field ID
        value: Current value
        field_type: Type of field ("phone", "date", "ssn", "currency", "text")
        
    Returns:
        Cleaned/normalized value
        
    Example:
        clean_field_value("66", "5551234567", "phone") -> "(555) 123-4567"
    """
    if not value or str(value).strip() == "":
        return value
    
    logger.info(f"[CLEAN] Cleaning field {field_id} as type '{field_type}'")
    
    if field_type == "phone":
        return normalize_phone_number(value)
    elif field_type == "date":
        return normalize_date(value)
    elif field_type == "ssn":
        return normalize_ssn(value)
    elif field_type == "currency":
        return normalize_currency(value)
    elif field_type == "text":
        # Just strip whitespace for text
        cleaned = str(value).strip()
        logger.debug(f"[CLEAN] Text field {field_id}: stripped whitespace")
        return cleaned
    else:
        # Unknown type, return as-is
        logger.debug(f"[CLEAN] Field {field_id}: unknown type '{field_type}', returning as-is")
        return value


@tool
def normalize_address(address: str) -> dict:
    """Parse and normalize address into components.
    
    Args:
        address: Full address string
        
    Returns:
        Dictionary with street, city, state, zip components
        
    Example:
        "123 Main St, Apt 4B, San Francisco, CA 94102"
        -> {"street": "123 Main St, Apt 4B", "city": "San Francisco", "state": "CA", "zip": "94102"}
    """
    if not address:
        return {"street": "", "city": "", "state": "", "zip": ""}
    
    address_str = str(address).strip()
    
    # Try to parse address (basic implementation)
    # Format expected: Street, City, State ZIP
    parts = [p.strip() for p in address_str.split(',')]
    
    result = {
        "street": "",
        "city": "",
        "state": "",
        "zip": ""
    }
    
    if len(parts) >= 1:
        result["street"] = parts[0]
    
    if len(parts) >= 2:
        result["city"] = parts[1]
    
    if len(parts) >= 3:
        # Last part should be "State ZIP"
        state_zip = parts[2].strip().split()
        if len(state_zip) >= 1:
            result["state"] = state_zip[0]
        if len(state_zip) >= 2:
            result["zip"] = state_zip[1]
    
    logger.debug(f"[NORMALIZE] Address: {address} -> {result}")
    return result

