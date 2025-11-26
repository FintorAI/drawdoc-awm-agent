"""Document extraction schemas - CSV-driven dynamic generation.

This module generates extraction schemas dynamically from DrawingDoc Verifications.csv.
Schemas are built based on the fields associated with each document type in the CSV.

REFERENCE: DrawingDoc Verifications.csv
----------------------------------------
This CSV file is the single source of truth for:
- Which fields should be extracted from each document type
- Field names and their Encompass field IDs
- Preferred document types for field extraction
"""

from typing import Any, Dict, List, Optional
import logging
from functools import lru_cache

from .csv_loader import get_csv_loader

logger = logging.getLogger(__name__)

# Cache for generated schemas to avoid regenerating on every call
_schema_cache: Dict[str, Optional[Dict[str, Any]]] = {}


def _field_name_to_schema_key(field_name: str) -> str:
    """Convert a field name to a schema property key.
    
    Args:
        field_name: Field name from CSV (e.g., "Borrower First Name")
        
    Returns:
        Schema key (e.g., "borrower_first_name")
    """
    # Convert to lowercase and replace spaces/special chars with underscores
    key = field_name.lower()
    key = key.replace(' ', '_')
    key = key.replace('-', '_')
    key = key.replace('/', '_')
    key = key.replace('(', '')
    key = key.replace(')', '')
    key = key.replace('.', '')
    key = key.replace(',', '')
    # Remove multiple underscores
    while '__' in key:
        key = key.replace('__', '_')
    # Remove leading/trailing underscores
    key = key.strip('_')
    return key


def _generate_schema_from_csv_fields(fields: List[Dict[str, str]]) -> Dict[str, Any]:
    """Generate a JSON schema from CSV field data.
    
    Args:
        fields: List of field dictionaries from CSV
        
    Returns:
        JSON schema dictionary
    """
    properties = {}
    
    for field in fields:
        field_name = field.get('name', '').strip()
        field_id = field.get('id', '').strip()
        notes = field.get('notes', '').strip()
        
        if not field_name:
            continue
        
        # Generate schema key
        key = _field_name_to_schema_key(field_name)
        
        # Determine field type based on field name
        field_type = "string"
        if any(word in field_name.lower() for word in ['amount', 'value', 'price', 'cost', 'fee', 'premium', 'number']):
            field_type = "number"
        elif any(word in field_name.lower() for word in ['date', 'year']):
            field_type = "string"  # Dates as strings for now
        
        # Build description with strict extraction instructions
        description = f"Extract the exact value for {field_name} as it appears in the document. "
        description += "ONLY return the literal text or number found in the document. "
        description += "Do NOT add interpretations, phrases, or placeholder text. "
        description += "If the field is not found, return an empty string or 0 (for numbers). "
        description += "Do NOT return phrases like 'not found' or 'N/A'."
        
        if field_id:
            description += f" Encompass Field ID: {field_id}."
        if notes:
            description += f" Notes: {notes}"
        
        properties[key] = {
            "type": field_type,
            "title": field_name,
            "description": description,
        }
    
    schema = {
        "type": "object",
        "properties": properties,
        "description": "Extract ONLY the exact values as they appear in the document. Do NOT add interpretations, explanations, or phrases. Return empty strings or 0 if values are not found."
    }
    
    return schema


def _get_fallback_schema(document_type: str) -> Optional[Dict[str, Any]]:
    """Get fallback schema for common document types not yet in CSV.
    
    This provides basic schemas for document types that haven't been added
    to the CSV yet. These should be migrated to CSV eventually.
    
    Args:
        document_type: Document type name
        
    Returns:
        Basic schema or None
    """
    doc_lower = document_type.lower().strip()
    
    # W-2 fallback (not in CSV yet)
    if doc_lower in ['w-2', 'w2', 'w-2 form']:
        logger.warning(f"Using fallback schema for '{document_type}'. Please add W-2 fields to CSV.")
        return {
            "type": "object",
            "description": "Extract ONLY the exact values as they appear in the document. Do NOT add interpretations, explanations, or phrases. Return empty strings or 0 if values are not found.",
            "properties": {
                "employee_first_name": {
                    "type": "string",
                    "title": "Employee First Name",
                    "description": "Extract the exact first name of the employee as it appears in the W-2 form. Only return the literal text found in the document. Do NOT add interpretations or phrases."
                },
                "employee_middle_name": {
                    "type": "string",
                    "title": "Employee Middle Name",
                    "description": "Extract the exact middle name or initial as it appears in the W-2 form. Only return the literal text found. Do NOT add interpretations or phrases."
                },
                "employee_last_name": {
                    "type": "string",
                    "title": "Employee Last Name",
                    "description": "Extract the exact last name as it appears in the W-2 form. Only return the literal text found. Do NOT add interpretations or phrases."
                },
                "employer_name": {
                    "type": "string",
                    "title": "Employer Name",
                    "description": "Extract the exact employer/company name as it appears in the W-2 form. Only return the literal text found. Do NOT add interpretations or phrases."
                },
                "tax_year": {
                    "type": "string",
                    "title": "Tax Year",
                    "description": "Extract the exact tax year as it appears in the W-2 form. Only return the literal text found. Do NOT add interpretations or phrases."
                }
            }
        }
    
    return None


def get_extraction_schema(document_type: str) -> Optional[Dict[str, Any]]:
    """Get extraction schema for a document type.
    
    This function dynamically generates schemas from CSV data. It looks up
    all fields associated with the document type in the CSV and generates
    a JSON schema for extraction.
    
    Schemas are cached to improve performance when processing multiple documents.
    
    If the document type is not in the CSV, it tries a fallback schema for
    common document types.
    
    Args:
        document_type: Document type (e.g., "W-2", "Final 1003", "Title Report")
        
    Returns:
        JSON schema dictionary or None if document type not found
        
    Example:
        >>> schema = get_extraction_schema("W-2")
        >>> print(schema["properties"].keys())
    """
    # Check cache first (performance optimization)
    if document_type in _schema_cache:
        return _schema_cache[document_type]
    
    loader = get_csv_loader()
    
    # Get fields for this document type from CSV
    fields = loader.get_fields_for_document(document_type)
    
    if not fields:
        # Try fallback schema for common types not yet in CSV
        fallback = _get_fallback_schema(document_type)
        if fallback:
            _schema_cache[document_type] = fallback
            return fallback
        
        logger.warning(f"No fields found in CSV for document type: {document_type}")
        _schema_cache[document_type] = None
        return None
    
    # Generate schema dynamically
    schema = _generate_schema_from_csv_fields(fields)
    
    # Cache the schema for future use
    _schema_cache[document_type] = schema
    
    logger.debug(f"Generated schema for {document_type} with {len(schema['properties'])} fields")
    return schema


def clear_schema_cache():
    """Clear the schema cache. Useful for testing or when CSV data changes."""
    global _schema_cache
    _schema_cache.clear()


def list_supported_document_types() -> List[str]:
    """Get list of all document types that have extraction schemas.
    
    This function returns all document types from the CSV that have
    associated fields defined.
    
    Returns:
        List of document type names
        
    Example:
        >>> doc_types = list_supported_document_types()
        >>> print(f"Supported types: {len(doc_types)}")
    """
    loader = get_csv_loader()
    document_types = loader.get_document_types()
    
    # Filter to only include document types that have fields
    supported = []
    for doc_type in document_types:
        fields = loader.get_fields_for_document(doc_type)
        if fields:
            supported.append(doc_type)
    
    return sorted(supported)


def get_fields_for_document_type(document_type: str) -> List[Dict[str, str]]:
    """Get all fields that should be extracted from a document type.
    
    Args:
        document_type: Document type name
        
    Returns:
        List of field dictionaries with keys: name, id, notes, is_primary
    """
    loader = get_csv_loader()
    return loader.get_fields_for_document(document_type)


def get_document_types_from_csv() -> List[str]:
    """Get all document types referenced in the CSV.
    
    Returns:
        List of document type names
    """
    loader = get_csv_loader()
    return loader.get_document_types()

