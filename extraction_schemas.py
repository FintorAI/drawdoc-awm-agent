"""Document extraction schemas for LandingAI.

This module contains JSON schemas for extracting structured data from different
document types. Each schema defines the fields to extract and their descriptions.

Usage:
    from extraction_schemas import get_extraction_schema
    
    schema = get_extraction_schema("W-2")
    result = extract_document_data(file_path, schema, "W-2")
"""

from typing import Any


# W-2 Form Schema - Tax wage and income statement
W2_SCHEMA = {
    "type": "object",
    "properties": {
        "employee_first_name": {
            "type": "string",
            "title": "Employee First Name",
            "description": "The first name of the employee from the W-2 form"
        },
        "employee_middle_name": {
            "type": "string",
            "title": "Employee Middle Name",
            "description": "The middle name or initial of the employee from the W-2 form"
        },
        "employee_last_name": {
            "type": "string",
            "title": "Employee Last Name",
            "description": "The last name of the employee from the W-2 form"
        },
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "The name of the employer/company from the W-2 form"
        },
        "tax_year": {
            "type": "string",
            "title": "Tax Year",
            "description": "The tax year for this W-2 form"
        }
    }
}


# Document type registry - maps document types to their schemas
DOCUMENT_SCHEMAS = {
    "W-2": W2_SCHEMA,
    "W2": W2_SCHEMA,  # Alternative naming
    "W-2 Form": W2_SCHEMA,
}


def get_extraction_schema(document_type: str) -> dict[str, Any]:
    """Get the extraction schema for a specific document type.
    
    Args:
        document_type: The type of document (e.g., "W-2", "Bank Statement", "1003")
        
    Returns:
        JSON schema dict for extracting data from that document type
        
    Raises:
        ValueError: If document type is not supported
        
    Example:
        >>> schema = get_extraction_schema("W-2")
        >>> result = extract_document_data(file_path, schema, "W-2")
    """
    # Normalize document type (case-insensitive lookup)
    normalized_type = document_type.strip()
    
    # Try exact match first
    if normalized_type in DOCUMENT_SCHEMAS:
        return DOCUMENT_SCHEMAS[normalized_type]
    
    # Try case-insensitive match
    for key, schema in DOCUMENT_SCHEMAS.items():
        if key.lower() == normalized_type.lower():
            return schema
    
    # Document type not found
    available_types = list(DOCUMENT_SCHEMAS.keys())
    raise ValueError(
        f"No extraction schema found for document type '{document_type}'. "
        f"Available types: {', '.join(available_types)}"
    )


def list_supported_document_types() -> list[str]:
    """Get list of all supported document types.
    
    Returns:
        List of document type names that have extraction schemas
        
    Example:
        >>> types = list_supported_document_types()
        >>> print(f"Supported: {', '.join(types)}")
    """
    return list(DOCUMENT_SCHEMAS.keys())

