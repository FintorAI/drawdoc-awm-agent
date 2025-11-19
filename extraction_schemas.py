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
        "employee_ssn": {
            "type": "string",
            "title": "Employee Social Security Number",
            "description": "The employee's Social Security Number from the W-2 form"
        },
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "The name of the employer/company from the W-2 form"
        },
        "employer_ein": {
            "type": "string",
            "title": "Employer EIN",
            "description": "The employer's Employer Identification Number"
        },
        "wages_tips_compensation": {
            "type": "string",
            "title": "Wages, Tips, and Other Compensation",
            "description": "Box 1 - Total wages, tips, and other compensation"
        },
        "tax_year": {
            "type": "string",
            "title": "Tax Year",
            "description": "The tax year for this W-2 form"
        }
    }
}


# Bank Statement Schema
BANK_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_holder_first_name": {
            "type": "string",
            "title": "Account Holder First Name",
            "description": "The first name of the account holder"
        },
        "account_holder_middle_name": {
            "type": "string",
            "title": "Account Holder Middle Name",
            "description": "The middle name or initial of the account holder"
        },
        "account_holder_last_name": {
            "type": "string",
            "title": "Account Holder Last Name",
            "description": "The last name of the account holder"
        },
        "account_number": {
            "type": "string",
            "title": "Account Number",
            "description": "The bank account number (last 4 digits or full number)"
        },
        "bank_name": {
            "type": "string",
            "title": "Bank Name",
            "description": "The name of the financial institution"
        },
        "statement_period_start": {
            "type": "string",
            "title": "Statement Period Start Date",
            "description": "The start date of the statement period"
        },
        "statement_period_end": {
            "type": "string",
            "title": "Statement Period End Date",
            "description": "The end date of the statement period"
        },
        "ending_balance": {
            "type": "string",
            "title": "Ending Balance",
            "description": "The ending balance on the statement"
        }
    }
}


# Pay Stub Schema
PAY_STUB_SCHEMA = {
    "type": "object",
    "properties": {
        "employee_first_name": {
            "type": "string",
            "title": "Employee First Name",
            "description": "The first name of the employee"
        },
        "employee_middle_name": {
            "type": "string",
            "title": "Employee Middle Name",
            "description": "The middle name or initial of the employee"
        },
        "employee_last_name": {
            "type": "string",
            "title": "Employee Last Name",
            "description": "The last name of the employee"
        },
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "The name of the employer/company"
        },
        "pay_period_start": {
            "type": "string",
            "title": "Pay Period Start Date",
            "description": "The start date of the pay period"
        },
        "pay_period_end": {
            "type": "string",
            "title": "Pay Period End Date",
            "description": "The end date of the pay period"
        },
        "gross_pay": {
            "type": "string",
            "title": "Gross Pay",
            "description": "The gross pay for this pay period"
        },
        "year_to_date_gross": {
            "type": "string",
            "title": "Year-to-Date Gross",
            "description": "The year-to-date gross earnings"
        }
    }
}


# Driver's License / ID Card Schema
DRIVERS_LICENSE_SCHEMA = {
    "type": "object",
    "properties": {
        "first_name": {
            "type": "string",
            "title": "First Name",
            "description": "The first name on the driver's license"
        },
        "middle_name": {
            "type": "string",
            "title": "Middle Name",
            "description": "The middle name or initial on the driver's license"
        },
        "last_name": {
            "type": "string",
            "title": "Last Name",
            "description": "The last name on the driver's license"
        },
        "date_of_birth": {
            "type": "string",
            "title": "Date of Birth",
            "description": "The date of birth on the driver's license"
        },
        "license_number": {
            "type": "string",
            "title": "License Number",
            "description": "The driver's license number"
        },
        "address": {
            "type": "string",
            "title": "Address",
            "description": "The street address on the driver's license"
        },
        "city": {
            "type": "string",
            "title": "City",
            "description": "The city on the driver's license"
        },
        "state": {
            "type": "string",
            "title": "State",
            "description": "The state on the driver's license"
        },
        "zip_code": {
            "type": "string",
            "title": "ZIP Code",
            "description": "The ZIP code on the driver's license"
        }
    }
}


# Document type registry - maps document types to their schemas
DOCUMENT_SCHEMAS = {
    "W-2": W2_SCHEMA,
    "W2": W2_SCHEMA,
    "W-2 Form": W2_SCHEMA,
    "Bank Statement": BANK_STATEMENT_SCHEMA,
    "Pay Stub": PAY_STUB_SCHEMA,
    "Paystub": PAY_STUB_SCHEMA,
    "Pay Stubs": PAY_STUB_SCHEMA,
    "Driver's License": DRIVERS_LICENSE_SCHEMA,
    "Drivers License": DRIVERS_LICENSE_SCHEMA,
    "ID Card": DRIVERS_LICENSE_SCHEMA,
    "Identification": DRIVERS_LICENSE_SCHEMA,
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

