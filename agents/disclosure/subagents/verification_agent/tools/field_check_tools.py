"""Field checking tools for disclosure verification agent."""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from packages.shared import get_encompass_client, load_field_mappings
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)


@tool
def check_required_fields(loan_id: str) -> dict:
    """Check if required disclosure fields have values in Encompass.
    
    This tool loads disclosure-required fields from the CSV (where required_disclosure='yes')
    and checks each one to see if it has a value in Encompass. It returns a summary of which 
    fields have values and which are missing.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - fields_checked: Total number of fields checked
        - fields_with_values: List of field IDs that have values
        - fields_missing: List of field IDs that are missing values
        - field_details: Dict mapping field_id to detailed status
    """
    logger.info(f"[CHECK] Checking required fields for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    all_fields = load_field_mappings()
    
    # Filter to only disclosure-required fields
    fields = [f for f in all_fields if f.get('required_disclosure', '').lower() == 'yes']
    
    logger.info(f"[CHECK] Found {len(fields)} disclosure-required fields out of {len(all_fields)} total")
    
    results = {
        "fields_checked": 0,
        "fields_with_values": [],
        "fields_missing": [],
        "field_details": {}
    }
    
    # Collect all field IDs for batch read
    field_ids_to_check = []
    field_id_to_name = {}
    
    for field in fields:
        field_id = field['field_id']
        field_name = field['name']
        
        # Skip fields without IDs
        if not field_id or field_id.strip() == '':
            continue
        
        field_ids_to_check.append(field_id)
        field_id_to_name[field_id] = field_name
    
    # Read all fields at once (more efficient)
    try:
        field_values = encompass.get_field(loan_id, field_ids_to_check)
        
        for field_id in field_ids_to_check:
            field_name = field_id_to_name[field_id]
            value = field_values.get(field_id)
            has_value = value is not None and str(value).strip() != ""
            
            results["fields_checked"] += 1
            results["field_details"][field_id] = {
                "name": field_name,
                "has_value": has_value,
                "value": value if has_value else None
            }
            
            if has_value:
                results["fields_with_values"].append(field_id)
                logger.debug(f"[CHECK] Field {field_id} ({field_name}): Has value")
            else:
                results["fields_missing"].append(field_id)
                logger.debug(f"[CHECK] Field {field_id} ({field_name}): Missing")
                
    except Exception as e:
        logger.error(f"[CHECK] Error checking fields: {e}")
        results["error"] = str(e)
    
    logger.info(f"[CHECK] Complete - Checked: {results['fields_checked']}, "
                f"With values: {len(results['fields_with_values'])}, "
                f"Missing: {len(results['fields_missing'])}")
    
    return results


@tool
def get_field_value(loan_id: str, field_id: str) -> dict:
    """Get a specific field value from Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID
        
    Returns:
        Dictionary with field_id, value, and has_value status
    """
    logger.info(f"[GET] Getting field {field_id} for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    try:
        result = encompass.get_field(loan_id, [field_id])
        value = result.get(field_id)
        has_value = value is not None and str(value).strip() != ""
        
        return {
            "field_id": field_id,
            "value": value,
            "has_value": has_value,
            "success": True
        }
    except Exception as e:
        logger.error(f"[GET] Error getting field {field_id}: {e}")
        return {
            "field_id": field_id,
            "error": str(e),
            "success": False
        }


@tool
def get_fields_by_document_type(loan_id: str, document_type: str) -> dict:
    """Get all disclosure-required field values for a specific document type.
    
    Args:
        loan_id: Encompass loan GUID
        document_type: Document type name (e.g., "Closing Disclosure", "Initial CD")
        
    Returns:
        Dictionary with fields for the document type and their values
    """
    logger.info(f"[GET_BY_DOC] Getting {document_type} fields for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    all_fields = load_field_mappings()
    
    # Filter to only disclosure-required fields and matching document type
    doc_fields = []
    for field in all_fields:
        if field.get('required_disclosure', '').lower() != 'yes':
            continue
            
        primary = field['primary_document'].lower()
        secondary = field['secondary_documents'].lower()
        doc_type_lower = document_type.lower()
        
        if doc_type_lower in primary or doc_type_lower in secondary:
            doc_fields.append(field)
    
    results = {
        "document_type": document_type,
        "fields_found": len(doc_fields),
        "fields": {}
    }
    
    # Collect field IDs for batch read
    field_ids_to_check = []
    field_id_to_name = {}
    
    for field in doc_fields:
        field_id = field['field_id']
        field_name = field['name']
        
        if not field_id or field_id.strip() == '':
            continue
        
        field_ids_to_check.append(field_id)
        field_id_to_name[field_id] = field_name
    
    # Read all fields at once
    if field_ids_to_check:
        try:
            field_values = encompass.get_field(loan_id, field_ids_to_check)
            
            for field_id in field_ids_to_check:
                field_name = field_id_to_name[field_id]
                value = field_values.get(field_id)
                has_value = value is not None and str(value).strip() != ""
                
                results["fields"][field_id] = {
                    "name": field_name,
                    "value": value,
                    "has_value": has_value
                }
        except Exception as e:
            logger.error(f"[GET_BY_DOC] Error reading fields: {e}")
            results["error"] = str(e)
    
    logger.info(f"[GET_BY_DOC] Found {len(results['fields'])} fields for {document_type}")
    
    return results

