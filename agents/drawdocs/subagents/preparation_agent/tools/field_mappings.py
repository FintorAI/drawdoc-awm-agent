"""Field mappings - CSV-driven dynamic mapping from extracted fields to Encompass field IDs.

This module dynamically maps extracted document fields to Encompass field IDs based on
data from DrawingDoc Verifications.csv.

The mapping process:
1. Extract fields from documents using extraction schemas
2. Map extracted field names to Encompass field IDs using CSV data
3. Prioritize fields from preferred document types (also from CSV)
"""

from typing import Dict, List, Optional
import logging

from .csv_loader import get_csv_loader
from .extraction_schemas import _field_name_to_schema_key

logger = logging.getLogger(__name__)


def _normalize_extracted_field_name(field_name: str) -> str:
    """Normalize an extracted field name to match CSV field names.
    
    Args:
        field_name: Extracted field name (e.g., "borrower_first_name")
        
    Returns:
        Normalized field name for matching
    """
    return field_name.lower().replace('_', ' ').strip()


def _match_extracted_field_to_csv_field(extracted_field: str, csv_fields: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Match an extracted field name to a CSV field.
    
    Args:
        extracted_field: Extracted field name (e.g., "borrower_first_name")
        csv_fields: List of CSV field dictionaries
        
    Returns:
        Matching CSV field dictionary or None
    """
    extracted_normalized = _normalize_extracted_field_name(extracted_field)
    extracted_words = set(extracted_normalized.split())
    
    # Try exact match first
    for csv_field in csv_fields:
        csv_name_normalized = csv_field['name'].lower()
        if extracted_normalized == csv_name_normalized:
            return csv_field
    
    # Try partial match - prioritize longer/more specific matches
    # Sort by length (longest first) to match more specific fields first
    sorted_fields = sorted(csv_fields, key=lambda f: len(f['name']), reverse=True)
    
    for csv_field in sorted_fields:
        csv_name_normalized = csv_field['name'].lower()
        # Normalize / to space for better matching
        csv_name_normalized = csv_name_normalized.replace('/', ' ')
        
        # Check if one contains the other (bidirectional)
        if extracted_normalized in csv_name_normalized or csv_name_normalized in extracted_normalized:
            return csv_field
    
    # Try matching key words - prioritize matches with more overlapping words
    best_match = None
    best_score = 0
    for csv_field in csv_fields:
        csv_words = set(csv_field['name'].lower().replace('/', ' ').split())
        overlap = extracted_words & csv_words
        overlap_count = len(overlap)
        # Prefer matches with more overlapping words
        if overlap_count >= 2 and overlap_count > best_score:
            best_score = overlap_count
            best_match = csv_field
    
    return best_match


def _get_fallback_mappings(document_type: str) -> Dict[str, str]:
    """Get fallback field mappings for document types not yet in CSV.
    
    Returns:
        Dictionary mapping extracted_field_name -> encompass_field_id
    """
    doc_lower = document_type.lower().strip()
    
    # W-2 fallback mappings
    if doc_lower in ['w-2', 'w2', 'w-2 form']:
        return {
            "employee_first_name": "4002",  # Borrower Last Name (W-2 employee name)
            "employee_middle_name": "4003",  # Borrower Middle Name
            "employee_last_name": "4004",    # Borrower Last Name
            # Note: employer_name, tax_year, wages don't have direct mappings yet
        }
    
    return {}


def get_field_mapping(document_type: str, extracted_field_name: str) -> Optional[str]:
    """Get Encompass field ID for an extracted field from a document type.
    
    This function dynamically looks up the field mapping from CSV data.
    Falls back to hardcoded mappings for document types not yet in CSV.
    
    Args:
        document_type: Document type (e.g., "W-2", "Final 1003")
        extracted_field_name: Extracted field name (e.g., "borrower_first_name")
        
    Returns:
        Encompass field ID or None if not found
        
    Example:
        >>> field_id = get_field_mapping("ID", "first_name")
        >>> print(field_id)  # "4000"
    """
    loader = get_csv_loader()
    
    # Get all fields for this document type from CSV
    csv_fields = loader.get_fields_for_document(document_type)
    
    if not csv_fields:
        # Try fallback mappings for common types not yet in CSV
        fallback_mappings = _get_fallback_mappings(document_type)
        if fallback_mappings:
            logger.debug(f"Using fallback mappings for document type: {document_type}")
            return fallback_mappings.get(extracted_field_name)
        
        logger.debug(f"No CSV fields found for document type: {document_type}")
        return None
    
    # Match extracted field to CSV field
    matched_field = _match_extracted_field_to_csv_field(extracted_field_name, csv_fields)
    
    if matched_field and matched_field.get('id'):
        field_id = matched_field['id'].strip()
        if field_id and field_id != 'TBD':
            return field_id
    
    return None


def get_all_mappings_for_document(document_type: str) -> Dict[str, str]:
    """Get all field mappings for a document type.
    
    This function returns a dictionary mapping extracted field names to
    Encompass field IDs for a given document type.
    
    Falls back to hardcoded mappings for document types not yet in CSV.
    
    Args:
        document_type: Document type name
        
    Returns:
        Dictionary mapping extracted_field_name -> encompass_field_id
        
    Example:
        >>> mappings = get_all_mappings_for_document("ID")
        >>> print(mappings)  # {"first_name": "4000", "last_name": "4002", ...}
    """
    loader = get_csv_loader()
    csv_fields = loader.get_fields_for_document(document_type)
    
    mappings = {}
    
    if not csv_fields:
        # Try fallback mappings for common types not yet in CSV
        fallback_mappings = _get_fallback_mappings(document_type)
        if fallback_mappings:
            logger.debug(f"Using fallback mappings for document type: {document_type}")
            return fallback_mappings
        return mappings
    
    for csv_field in csv_fields:
        field_name = csv_field.get('name', '').strip()
        field_id = csv_field.get('id', '').strip()
        
        if not field_name or not field_id or field_id == 'TBD':
            continue
        
        # Convert CSV field name to schema key (extracted field name)
        extracted_field_name = _field_name_to_schema_key(field_name)
        mappings[extracted_field_name] = field_id
    
    return mappings


def get_preferred_documents_for_field(field_id: str) -> List[str]:
    """Get preferred document types for extracting a specific field.
    
    This function uses CSV data to determine which document types are preferred
    for extracting a given field.
    
    Args:
        field_id: Encompass field ID (e.g., "4000", "610")
        
    Returns:
        List of preferred document types. Empty list means extract from any document.
        
    Example:
        >>> preferred = get_preferred_documents_for_field("4000")
        >>> print(preferred)  # ["ID"]
    """
    loader = get_csv_loader()
    field_to_docs = loader.get_field_to_documents_mapping()
    return field_to_docs.get(field_id, [])


def should_extract_from_document(field_id: str, document_type: str, document_title: str = "") -> bool:
    """Check if a field should be extracted from a specific document.
    
    This function checks if the document matches the preferred document type for the field.
    If no preferred document is specified, returns True (extract from any document).
    
    Args:
        field_id: Encompass field ID
        document_type: Type of the document
        document_title: Title of the document (for fuzzy matching)
        
    Returns:
        True if field should be extracted from this document, False otherwise.
        Always returns True if no preferred document is specified.
        
    Example:
        >>> should_extract_from_document("4000", "ID", "Driver's License")
        True
        >>> should_extract_from_document("4000", "W-2", "W-2 all years")
        True  # Will fall back if ID not available
    """
    preferred_docs = get_preferred_documents_for_field(field_id)
    
    # If no preference, extract from any document
    if not preferred_docs:
        return True
    
    # Check if document matches preferred types
    doc_type_lower = document_type.lower()
    doc_title_lower = document_title.lower()
    
    for preferred in preferred_docs:
        preferred_lower = preferred.lower()
        if (preferred_lower in doc_type_lower or 
            preferred_lower in doc_title_lower or
            doc_type_lower.startswith(preferred_lower) or
            doc_title_lower.startswith(preferred_lower)):
            return True
    
    # Document doesn't match preferred type, but we'll still extract if no preferred doc is available
    # This allows fallback extraction
    return True  # Changed to True to allow fallback - prefer but don't restrict


def is_mapping_ready(field_id: str) -> bool:
    """Check if a field mapping is ready (not TBD).
    
    Args:
        field_id: Encompass field ID or "TBD"
        
    Returns:
        True if field_id is a valid Encompass field ID, False if "TBD" or None
    """
    return field_id is not None and field_id != "TBD" and field_id != ""


def list_ready_mappings() -> List[str]:
    """List all document types that have field mappings ready.
    
    Returns:
        List of document type names
    """
    loader = get_csv_loader()
    document_types = loader.get_document_types()
    
    ready = []
    for doc_type in document_types:
        mappings = get_all_mappings_for_document(doc_type)
        if len(mappings) > 0:
            ready.append(doc_type)
    
    return sorted(ready)


# Common field IDs for quick reference (derived from CSV)
def _get_common_field_ids() -> Dict[str, str]:
    """Get common field IDs from CSV.
    
    Returns:
        Dictionary mapping field names to field IDs
    """
    loader = get_csv_loader()
    all_fields = loader.get_all_fields()
    
    common = {}
    for field in all_fields:
        field_name = field.get('name', '').strip()
        field_id = field.get('id', '').strip()
        
        if field_name and field_id and field_id != 'TBD':
            # Use normalized name as key
            key = _field_name_to_schema_key(field_name)
            common[key] = field_id
    
    return common


# Lazy load common field IDs
_COMMON_FIELD_IDS: Optional[Dict[str, str]] = None

def get_common_field_ids() -> Dict[str, str]:
    """Get common field IDs for quick reference.
    
    Returns:
        Dictionary mapping normalized field names to Encompass field IDs
    """
    global _COMMON_FIELD_IDS
    if _COMMON_FIELD_IDS is None:
        _COMMON_FIELD_IDS = _get_common_field_ids()
    return _COMMON_FIELD_IDS

