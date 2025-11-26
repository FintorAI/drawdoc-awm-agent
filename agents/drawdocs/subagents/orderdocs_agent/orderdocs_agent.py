"""
OrderDocs Agent - Reads field values from Encompass based on document types

This agent reads field values from Encompass based on document types specified in input.
It uses the CSV file to determine which field IDs correspond to each document type,
then reads those field values from Encompass and returns them in JSON format.

Example:
    Input: {"loan_id": "...", "document_types": ["ID"]}
    Output: {"4000": "Jane", "4001": "Doe", "4002": "Smith"}
"""

import os
import sys
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from langchain_core.tools import tool

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load .env from parent directories
    env_paths = [
        Path(__file__).parent.parent.parent.parent / ".env",
        Path(__file__).parent.parent.parent.parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger = logging.getLogger(__name__)
            logger.debug(f"Loaded .env from: {env_path}")
            break
except ImportError:
    pass  # dotenv not installed, rely on system environment variables

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import Encompass client - use same pattern as preparation_agent
from copilotagent import EncompassConnect

def _get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables."""
    # Verify required credentials are present
    required_vars = [
        "ENCOMPASS_ACCESS_TOKEN",
        "ENCOMPASS_CLIENT_ID",
        "ENCOMPASS_CLIENT_SECRET",
        "ENCOMPASS_INSTANCE_ID",
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
    
    return EncompassConnect(
        access_token=os.getenv("ENCOMPASS_ACCESS_TOKEN", ""),
        api_base_url=os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com"),
        credentials={
            "username": os.getenv("ENCOMPASS_USERNAME", ""),
            "password": os.getenv("ENCOMPASS_PASSWORD", ""),
            "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
            "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
            "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
            "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        },
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to show field parsing details
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# CSV file path - use the Sheet1 version in data folder
CSV_PATH = Path(__file__).parent.parent.parent.parent.parent / "packages" / "data" / "DrawingDoc Verifications - Sheet1.csv"


def _load_csv_fields() -> List[Dict[str, str]]:
    """Load field mappings from CSV file.
    
    Returns:
        List of dictionaries with field information
    """
    if not CSV_PATH.exists():
        logger.error(f"CSV file not found: {CSV_PATH}")
        return []
    
    fields = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                fields.append({
                    'name': row.get('Name', '').strip(),
                    'field_id': row.get('ID', '').strip(),
                    'primary_document': row.get('Primary document', '').strip(),
                    'secondary_documents': row.get('Secondary documents', '').strip(),
                })
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []
    
    return fields


def _parse_and_validate_field_id(field_id: str, field_name: str = "") -> List[str]:
    """Parse field ID string and return all field IDs (keep everything from CSV).
    
    Handles cases like:
    - "4000" -> ["4000"]
    - "1041 | 1553 | HMDA.X11" -> ["1041", "1553", "HMDA.X11"] (keep all)
    - "324 | CD5.X18" -> ["324", "CD5.X18"] (keep all)
    - "Loan TeamMember Name Doc Drawer" -> ["Loan TeamMember Name Doc Drawer"] (keep as-is)
    - "AuditTrail" -> ["AuditTrail"] (keep as-is)
    
    Args:
        field_id: Field ID string from CSV
        field_name: Field name for debugging
        
    Returns:
        List of all field IDs from CSV (no filtering)
    """
    if not field_id or field_id.strip() == '':
        logger.debug(f"[PARSE] Field '{field_name}': Empty field_id")
        return []
    
    # Split by | if multiple field IDs, otherwise keep as single ID
    if '|' in field_id:
        parts = [p.strip() for p in field_id.split('|')]
        # Filter out empty parts
        parts = [p for p in parts if p]
        logger.debug(f"[PARSE] Field '{field_name}': Split '{field_id}' into {len(parts)} IDs: {parts}")
        return parts
    else:
        # Single field ID - return as-is
        field_id_clean = field_id.strip()
        logger.debug(f"[PARSE] Field '{field_name}': Single ID '{field_id_clean}'")
        return [field_id_clean]


def get_field_ids_for_document_types(document_types: List[str]) -> Dict[str, List[str]]:
    """Get field IDs for specified document types from CSV.
    
    Includes fields where the document type appears in primary OR secondary columns (or both).
    
    Args:
        document_types: List of document type names (e.g., ["ID", "Title Report"])
        
    Returns:
        Dictionary mapping document_type -> list of valid field IDs (fields in primary or secondary)
    """
    all_fields = _load_csv_fields()
    
    # Normalize document types for matching (case-insensitive)
    doc_types_lower = {dt.lower().strip(): dt for dt in document_types}
    
    # Map document type -> field IDs
    doc_to_field_ids: Dict[str, List[str]] = {dt: [] for dt in document_types}
    
    logger.info(f"[CSV] Loading fields from CSV: {CSV_PATH}")
    logger.info(f"[CSV] Total fields in CSV: {len(all_fields)}")
    logger.info(f"[CSV] Filtering: Fields where document type appears in primary OR secondary columns")
    
    for field in all_fields:
        field_name = field['name']
        field_id_str = field['field_id']
        primary_doc = field['primary_document']
        secondary_docs = field['secondary_documents']
        
        logger.debug(f"[CSV] Processing field: '{field_name}' | ID: '{field_id_str}' | Primary: '{primary_doc}' | Secondary: '{secondary_docs}'")
        
        if not field_id_str or field_id_str == '':
            logger.debug(f"[CSV] Field '{field_name}': No field ID - skipping")
            continue
        
        # Parse and validate field ID(s)
        valid_field_ids = _parse_and_validate_field_id(field_id_str, field_name)
        if not valid_field_ids:
            logger.debug(f"[CSV] Field '{field_name}': No valid field IDs after parsing - skipping")
            continue  # Skip fields with no valid IDs
        
        logger.debug(f"[CSV] Field '{field_name}': Parsed {len(valid_field_ids)} valid IDs: {valid_field_ids}")
        
        # Normalize primary document for matching
        primary_doc_lower = primary_doc.lower().strip() if primary_doc else ""
        
        # Parse secondary documents (semicolon-separated, case-insensitive)
        secondary_docs_list = []
        if secondary_docs and secondary_docs.strip():
            secondary_docs_list = [doc.strip().lower() for doc in secondary_docs.split(';') if doc.strip()]
        
        # Check each requested document type
        for doc_type_lower, doc_type in doc_types_lower.items():
            # Check if document type appears in primary OR secondary (or both)
            # Match if exact match or document type is contained in the doc string
            in_primary = (
                primary_doc_lower == doc_type_lower or
                doc_type_lower in primary_doc_lower or
                primary_doc_lower in doc_type_lower
            ) if primary_doc_lower else False
            
            in_secondary = (
                doc_type_lower in secondary_docs_list or
                any(doc_type_lower in sec_doc or sec_doc in doc_type_lower for sec_doc in secondary_docs_list)
            ) if secondary_docs_list else False
            
            # Include if document type is in primary OR secondary (or both)
            if in_primary or in_secondary:
                match_type = "BOTH" if (in_primary and in_secondary) else ("PRIMARY" if in_primary else "SECONDARY")
                logger.debug(f"[CSV] Field '{field_name}': Matched {match_type} for document '{doc_type}'")
                # Add all field IDs for this field to the document type
                for field_id in valid_field_ids:
                    if field_id not in doc_to_field_ids[doc_type]:
                        doc_to_field_ids[doc_type].append(field_id)
                        logger.debug(f"[CSV] Added field ID '{field_id}' for document '{doc_type}'")
    
    return doc_to_field_ids


@tool
def read_document_fields(
    loan_id: str,
    document_types: List[str]
) -> Dict[str, Any]:
    """Read field values from Encompass for specified document types.
    
    This tool:
    1. Looks up field IDs for each document type from the CSV file
    2. Reads those field values from Encompass
    3. Returns all field values (including empty ones) in JSON format with has_value flag
    
    Args:
        loan_id: The Encompass loan GUID
        document_types: List of document types (e.g., ["ID", "Title Report"])
        
    Returns:
        Dictionary with field_id -> {"value": value, "has_value": bool} mappings for all requested document types
        
    Example:
        >>> read_document_fields("loan-guid", ["ID"])
        {
            "4000": {"value": "Jane", "has_value": true},
            "4001": {"value": "Doe", "has_value": true},
            "4002": {"value": "", "has_value": false}
        }
    """
    logger.info(f"[READ_DOC_FIELDS] Starting - Loan: {loan_id[:8]}..., Document types: {document_types}")
    
    # Get field IDs for each document type
    doc_to_field_ids = get_field_ids_for_document_types(document_types)
    
    # Collect all unique field IDs
    all_field_ids: Set[str] = set()
    for field_ids in doc_to_field_ids.values():
        all_field_ids.update(field_ids)
    
    if not all_field_ids:
        logger.warning(f"[READ_DOC_FIELDS] No field IDs found for document types: {document_types}")
        return {}
    
    # Log which fields will be read for each document type
    for doc_type, field_ids in doc_to_field_ids.items():
        logger.info(f"[READ_DOC_FIELDS] Document '{doc_type}': {len(field_ids)} fields")
        if field_ids:
            logger.debug(f"[READ_DOC_FIELDS] Field IDs for '{doc_type}': {field_ids[:10]}...")  # Show first 10
    
    # Read field values from Encompass
    try:
        client = _get_encompass_client()
        field_ids_list = list(all_field_ids)
        
        logger.info(f"[READ_DOC_FIELDS] Attempting to read {len(field_ids_list)} field IDs from Encompass")
        
        try:
            field_values = client.get_field(loan_id, field_ids_list)
            
            # Check if all fields were successfully read
            read_count = len(field_values)
            logger.info(f"[READ_DOC_FIELDS] Success - Read {read_count} field values")
            
            # Return all field values with has_value flag
            # Format: {field_id: {"value": value, "has_value": bool}}
            result = {}
            for field_id in all_field_ids:
                value = field_values.get(field_id, None)
                
                # Determine if value is populated (not None, not empty string)
                has_value = False
                if value is not None:
                    # Check if it's a non-empty string or other truthy value
                    if isinstance(value, str):
                        has_value = value.strip() != ""
                    else:
                        has_value = bool(value)
                
                result[field_id] = {
                    "value": value,
                    "has_value": has_value
                }
            
            return result
            
        except Exception as api_error:
            error_str = str(api_error)
            
            # Check if it's a 400 error with invalid field IDs
            if "Invalid field id" in error_str or ("400" in error_str and "Bad Request" in error_str):
                logger.warning(f"[READ_DOC_FIELDS] Some field IDs are invalid. Parsing error to identify bad IDs...")
                logger.debug(f"[READ_DOC_FIELDS] Full error: {error_str}")
                
                # Try to extract invalid field IDs from error message
                import re
                import json
                invalid_ids = set()
                
                # Try to parse JSON from error message
                try:
                    # Extract JSON part from error string
                    json_start = error_str.find('{')
                    if json_start != -1:
                        json_str = error_str[json_start:]
                        error_json = json.loads(json_str)
                        
                        # Look for errors array
                        if 'errors' in error_json:
                            for error_item in error_json['errors']:
                                if 'details' in error_item:
                                    detail = error_item['details']
                                    # Extract field ID from "Invalid field id: 'FieldID'"
                                    match = re.search(r"Invalid field id: '([^']+)'", detail)
                                    if match:
                                        invalid_ids.add(match.group(1))
                except Exception as parse_error:
                    logger.debug(f"[READ_DOC_FIELDS] Could not parse JSON from error: {parse_error}")
                    # Fallback to regex pattern matching
                    invalid_matches = re.findall(r"Invalid field id: '([^']+)'", error_str)
                    invalid_ids.update(invalid_matches)
                
                logger.warning(f"[READ_DOC_FIELDS] Found {len(invalid_ids)} invalid field IDs (will skip): {list(invalid_ids)}")
                
                # Filter out invalid IDs and retry
                valid_field_ids = [fid for fid in field_ids_list if fid not in invalid_ids]
                
                if not valid_field_ids:
                    logger.error(f"[READ_DOC_FIELDS] All field IDs were invalid!")
                    return {}  # Return empty dict if all IDs are invalid
                
                logger.info(f"[READ_DOC_FIELDS] Retrying with {len(valid_field_ids)} valid field IDs (skipped {len(invalid_ids)} invalid)")
                
                # Retry with only valid field IDs
                try:
                    field_values = client.get_field(loan_id, valid_field_ids)
                    
                    logger.info(f"[READ_DOC_FIELDS] Success on retry - Read {len(field_values)} field values")
                    
                    # Return only valid field values with has_value flag
                    # Format: {field_id: {"value": value, "has_value": bool}}
                    result = {}
                    for field_id in valid_field_ids:
                        value = field_values.get(field_id, None)
                        
                        # Determine if value is populated (not None, not empty string)
                        has_value = False
                        if value is not None:
                            # Check if it's a non-empty string or other truthy value
                            if isinstance(value, str):
                                has_value = value.strip() != ""
                            else:
                                has_value = bool(value)
                        
                        result[field_id] = {
                            "value": value,
                            "has_value": has_value
                        }
                    
                    return result
                    
                except Exception as retry_error:
                    logger.error(f"[READ_DOC_FIELDS] Error on retry: {retry_error}")
                    return {"error": str(retry_error)}
            else:
                # Other types of errors (401, 500, etc.)
                logger.error(f"[READ_DOC_FIELDS] Error reading fields: {api_error}")
                raise
        
    except Exception as e:
        logger.error(f"[READ_DOC_FIELDS] Unexpected error: {e}")
        return {"error": str(e)}


def process_orderdocs_request(input_json: Dict[str, Any]) -> Dict[str, Any]:
    """Process an orderdocs request.
    
    Args:
        input_json: Dictionary with loan_id and document_types
        
    Returns:
        Dictionary with field_id -> value mappings
        
    Example input:
        {
            "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
            "document_types": ["ID", "Title Report"]
        }
        
    Example output:
        {
            "4000": "Jane",
            "4001": "Doe",
            "1109": "132275.0",
            "356": "290000"
        }
    """
    # Validate input
    if "loan_id" not in input_json:
        return {
            "error": "Missing required field: loan_id",
            "expected_format": {
                "loan_id": "string (required)",
                "document_types": "array of strings (required)"
            }
        }
    
    if "document_types" not in input_json or not input_json["document_types"]:
        return {
            "error": "Missing required field: document_types",
            "expected_format": {
                "loan_id": "string (required)",
                "document_types": "array of strings (required)"
            }
        }
    
    loan_id = input_json["loan_id"]
    document_types = input_json["document_types"]
    
    if not isinstance(document_types, list):
        return {
            "error": "document_types must be a list",
            "loan_id": loan_id
        }
    
    logger.info(f"[ORDERDOCS] Processing - Loan: {loan_id[:8]}..., Document types: {document_types}")
    
    try:
        # Read fields for all document types
        result = read_document_fields.invoke({
            "loan_id": loan_id,
            "document_types": document_types
        })
        
        return result
        
    except Exception as e:
        logger.error(f"[ORDERDOCS] Error processing request: {e}")
        return {
            "error": str(e),
            "loan_id": loan_id
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OrderDocs Agent - Read field values from Encompass based on document types"
    )
    parser.add_argument("--json", type=str, help="JSON input as string")
    parser.add_argument("--json-file", type=str, help="Path to JSON input file")
    
    args = parser.parse_args()
    
    # Handle JSON input
    if args.json or args.json_file:
        if args.json:
            input_data = json.loads(args.json)
        else:
            with open(args.json_file, 'r') as f:
                input_data = json.load(f)
        
        result = process_orderdocs_request(input_data)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    
    # If no arguments, show usage
    parser.print_help()
    sys.exit(1)

