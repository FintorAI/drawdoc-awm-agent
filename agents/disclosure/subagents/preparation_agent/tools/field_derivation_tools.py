"""AI-based field derivation tools for disclosure preparation agent.

These tools allow the AI agent to intelligently search for and derive field values
without hardcoded rules. The agent uses reasoning to figure out relationships.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from packages.shared import get_encompass_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)


@tool
def get_loan_field_value(loan_id: str, field_id: str) -> dict:
    """Get a specific field value from Encompass.
    
    Use this tool to read any field from Encompass. Good for checking related
    fields when trying to derive a missing value.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID to retrieve
        
    Returns:
        Dictionary with field_id, value, and status
        
    Example:
        To get borrower first name: get_loan_field_value(loan_id, "4000")
    """
    logger.info(f"[GET] Getting field {field_id} for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    try:
        result = encompass.get_field(loan_id, [field_id])
        value = result.get(field_id)
        has_value = value is not None and str(value).strip() != ""
        
        logger.debug(f"[GET] Field {field_id}: {value if has_value else '(empty)'}")
        
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
def search_loan_fields(loan_id: str, search_term: str) -> dict:
    """Search field names from CSV for a term, then read their values.
    
    Use this to find fields that might contain related information. For example,
    if you need an email address, search for "email" to find all email-related fields.
    
    Args:
        loan_id: Encompass loan GUID
        search_term: What to search for (e.g., "email", "phone", "address")
        
    Returns:
        Dictionary with matching fields and their values
        
    Example:
        If you need "Borrower Email" but it's empty, search for "email" to find
        other email fields that might have the value you need.
    """
    logger.info(f"[SEARCH] Searching for '{search_term}' in loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    try:
        # Get field mappings from CSV
        from packages.shared import load_field_mappings
        all_fields = load_field_mappings()
        
        # Search for matching fields by name (case-insensitive)
        search_lower = search_term.lower()
        matching_field_ids_set = set()  # Use set to avoid duplicates
        field_id_to_name = {}
        
        for field in all_fields:
            field_name = field.get('name', '').lower()
            field_id = field.get('field_id', '')
            
            # Skip empty field IDs
            if not field_id or field_id.strip() == '':
                continue
            
            # Check if search term appears in field name
            if search_lower in field_name:
                matching_field_ids_set.add(field_id)  # Add to set (auto-deduplicates)
                field_id_to_name[field_id] = field.get('name', 'Unknown')
        
        # Convert set back to list
        matching_field_ids = list(matching_field_ids_set)
        
        # Read values for matching fields
        matches = {}
        if matching_field_ids:
            field_values = encompass.get_field(loan_id, matching_field_ids)
            
            for field_id in matching_field_ids:
                value = field_values.get(field_id)
                has_value = value is not None and str(value).strip() != ""
                matches[field_id] = {
                    "name": field_id_to_name[field_id],
                    "value": value if has_value else None,
                    "has_value": has_value
                }
        
        logger.info(f"[SEARCH] Found {len(matches)} matching fields")
        
        return {
            "search_term": search_term,
            "matches": matches,
            "count": len(matches),
            "success": True
        }
    except Exception as e:
        logger.error(f"[SEARCH] Error searching for '{search_term}': {e}")
        return {
            "search_term": search_term,
            "error": str(e),
            "success": False
        }


@tool
def write_field_value(loan_id: str, field_id: str, value: Any, dry_run: bool = True) -> dict:
    """Write a value to an Encompass field.
    
    Use this after deriving or finding the correct value for a field. By default,
    runs in dry-run mode (no actual write) for safety.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID to write to
        value: Value to write
        dry_run: If True, only simulate the write (default: True)
        
    Returns:
        Dictionary with write status
        
    Example:
        After finding the correct email value:
        write_field_value(loan_id, "EMAIL_FIELD_ID", "borrower@example.com", dry_run=True)
    """
    logger.info(f"[WRITE] {'[DRY RUN] ' if dry_run else ''}Writing field {field_id} for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    if dry_run:
        logger.info(f"[WRITE] [DRY RUN] Would write {field_id} = {value}")
        return {
            "field_id": field_id,
            "value": value,
            "dry_run": True,
            "message": f"[DRY RUN] Would write {field_id} = {value}",
            "success": True
        }
    
    try:
        success = encompass.write_field(loan_id, field_id, value)
        logger.info(f"[WRITE] Successfully wrote {field_id} = {value}")
        return {
            "field_id": field_id,
            "value": value,
            "dry_run": False,
            "success": success,
            "message": f"Wrote {field_id} = {value}"
        }
    except Exception as e:
        logger.error(f"[WRITE] Error writing field {field_id}: {e}")
        return {
            "field_id": field_id,
            "value": value,
            "error": str(e),
            "success": False
        }


@tool
def get_multiple_field_values(loan_id: str, field_ids: List[str]) -> dict:
    """Get multiple field values at once.
    
    Use this to efficiently read several related fields together.
    
    Args:
        loan_id: Encompass loan GUID
        field_ids: List of field IDs to retrieve
        
    Returns:
        Dictionary mapping field_id to value
        
    Example:
        To check borrower name fields:
        get_multiple_field_values(loan_id, ["4000", "4002", "36"])
    """
    logger.info(f"[GET_MULTIPLE] Getting {len(field_ids)} fields for loan {loan_id[:8]}...")
    
    encompass = get_encompass_client()
    
    try:
        # Deduplicate field IDs to avoid API errors
        unique_field_ids = list(set(field_ids))
        if len(unique_field_ids) < len(field_ids):
            logger.warning(f"[GET_MULTIPLE] Removed {len(field_ids) - len(unique_field_ids)} duplicate field IDs")
        
        # Read all fields at once (more efficient than individual calls)
        field_values = encompass.get_field(loan_id, unique_field_ids)
        
        results = {}
        for field_id in field_ids:
            value = field_values.get(field_id)
            has_value = value is not None and str(value).strip() != ""
            results[field_id] = {
                "value": value if has_value else None,
                "has_value": has_value
            }
        
        logger.info(f"[GET_MULTIPLE] Retrieved {len(results)} fields")
        
        return {
            "loan_id": loan_id,
            "fields": results,
            "success": True
        }
    except Exception as e:
        logger.error(f"[GET_MULTIPLE] Error getting fields: {e}")
        return {
            "loan_id": loan_id,
            "error": str(e),
            "success": False
        }

