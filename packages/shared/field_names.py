"""Field ID to human-readable name mapping.

Auto-generated from master_field_data.csv for better logging.
Maps Encompass field IDs to their human-readable names.
"""

import csv
from pathlib import Path
from typing import Dict, Optional

# Cache for field names loaded from CSV
_FIELD_NAMES_CACHE: Optional[Dict[str, str]] = None


def _load_field_names() -> Dict[str, str]:
    """Load field names from master_field_data.csv."""
    global _FIELD_NAMES_CACHE
    
    if _FIELD_NAMES_CACHE is not None:
        return _FIELD_NAMES_CACHE
    
    field_names = {}
    csv_path = Path(__file__).parent.parent.parent / "master_field_data.csv"
    
    if not csv_path.exists():
        # Fallback to basic mapping if CSV not found
        return _get_basic_field_names()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # CSV format: Category, Description, Field ID, (empty column)
                field_id = row.get('Field ID', '').strip().rstrip(',')
                description = row.get('Description', '').strip()
                if field_id and description:
                    field_names[field_id] = description
    except Exception as e:
        # If CSV loading fails, use basic mapping
        return _get_basic_field_names()
    
    _FIELD_NAMES_CACHE = field_names
    return field_names


def _get_basic_field_names() -> Dict[str, str]:
    """Fallback field name mapping if CSV is not available."""
    return {
        # Borrower
        "4000": "Borrower First Name",
        "4002": "Borrower Last Name",
        "65": "Borrower SSN",
        "66": "Borrower Home Phone",
        "1240": "Borrower Email",
        "FE0117": "Borrower Business Phone",
        
        # Property
        "11": "Property Address",
        "12": "Property City",
        "14": "Property State",
        "15": "Property Zip",
        "1041": "Property Type",
        "1811": "Occupancy",
        
        # Loan
        "1109": "Loan Amount",
        "3": "Note Rate",
        "4": "Loan Term",
        "1172": "Loan Type",
        "19": "Loan Purpose",
        "353": "LTV",
        "976": "Combined LTV",
        "356": "Appraised Value",
        "136": "Purchase Price",
        
        # TRID/Dates
        "745": "Application Date",
        "748": "Closing Date",
        "761": "Lock Date",
        "762": "Lock Expiration Date",
        "LE1.X1": "LE Date Issued",
        "3152": "TIL Initial Disclosure Date",
        
        # RegZ-LE
        "672": "Late Charge Days",
        "673": "Late Charge Percent",
        "664": "Prepayment Penalty",
        "1176": "Interest Days Per Year",
        "1751": "Buydown Indicator",
        
        # Loan Officer
        "317": "Loan Officer Name",
        "3238": "LO NMLS ID",
        "3330": "LO Company NMLS",
        "3322": "Branch NMLS",
        
        # Status
        "1393": "Loan Status",
        "2626": "Loan Channel",
        "2400": "Loan Is Locked",
    }


def get_field_name(field_id: str) -> str:
    """Get human-readable name for a field ID.
    
    Args:
        field_id: Encompass field ID (e.g., "4000", "LE1.X1")
        
    Returns:
        Human-readable field name or "Field {field_id}" if not found
        
    Example:
        >>> get_field_name("4000")
        "Borrower First Name"
        >>> get_field_name("UNKNOWN")
        "Field UNKNOWN"
    """
    field_names = _load_field_names()
    return field_names.get(field_id, f"Field {field_id}")


def get_field_names_batch(field_ids: list[str]) -> Dict[str, str]:
    """Get field names for multiple field IDs at once.
    
    Args:
        field_ids: List of field IDs
        
    Returns:
        Dictionary mapping field_id to field_name
    """
    field_names = _load_field_names()
    return {
        field_id: field_names.get(field_id, f"Field {field_id}")
        for field_id in field_ids
    }


def reload_field_names() -> None:
    """Force reload of field names from CSV (useful for testing)."""
    global _FIELD_NAMES_CACHE
    _FIELD_NAMES_CACHE = None

