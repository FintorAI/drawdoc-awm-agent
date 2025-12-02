"""
Field lookup tools for the Verification Sub-Agent.

These tools handle field ID lookup and retrieving missing field values from Encompass.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict
from langchain_core.tools import tool
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from copilotagent import EncompassConnect

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


def _get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables."""
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


@tool
def get_field_id_from_name(
    field_name: str,
    field_mapping: dict
) -> str:
    """
    Map field name to field ID using CSV mapping.
    
    Looks up the field ID for a given field name from the field mapping configuration.
    
    Args:
        field_name: The field name to look up (e.g., "Borrower First Name")
        field_mapping: Field mapping configuration from CSV
        
    Returns:
        The field ID if found, or error message if not found
    """
    # Direct lookup
    for field_id, mapping in field_mapping.items():
        if mapping.get("field_name", "").lower() == field_name.lower():
            return field_id
    
    # Partial match
    for field_id, mapping in field_mapping.items():
        mapped_name = mapping.get("field_name", "").lower()
        if field_name.lower() in mapped_name or mapped_name in field_name.lower():
            return field_id
    
    return f"Field name '{field_name}' not found in field mapping"


@tool
def get_missing_field_value(
    loan_id: str,
    field_id: str
) -> dict[str, Any]:
    """
    Fetch field value from Encompass if not in prep output.
    
    Uses primitives read_fields to retrieve the current value from Encompass via MCP server.
    Only used when field_value is missing from prep output.
    
    Args:
        loan_id: The Encompass loan GUID
        field_id: The field ID to retrieve
        
    Returns:
        Dictionary containing:
        - field_id: The field ID
        - value: The field value (if found)
        - found: True if value exists, False otherwise
        - error: Error message if retrieval failed
    """
    try:
        # Use primitives for field reading (MCP server)
        from agents.drawdocs.tools import read_fields
        result = read_fields(loan_id, [field_id])
        
        if field_id in result:
            value = result[field_id]
            return {
                "field_id": field_id,
                "value": value,
                "found": value is not None and str(value).strip() != "",
                "error": None
            }
        else:
            return {
                "field_id": field_id,
                "value": None,
                "found": False,
                "error": f"Field {field_id} not found in loan"
            }
    
    except Exception as e:
        return {
            "field_id": field_id,
            "value": None,
            "found": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """Test the field lookup tools."""
    print("Field lookup tools loaded successfully")
    print(f"Available tools: get_field_id_from_name, get_missing_field_value")

