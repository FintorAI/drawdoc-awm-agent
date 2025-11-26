"""Verification Sub-Agent for disclosure field checks.

This agent checks if all required disclosure fields have values in Encompass.
It provides tools to check individual fields, all fields, or fields by document type.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from copilotagent import create_deep_agent
from agents.disclosure.subagents.verification_agent.tools.field_check_tools import (
    check_required_fields,
    get_field_value,
    get_fields_by_document_type
)

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

verification_instructions = """You are a Disclosure Verification Sub-Agent.

Your job is to check if all required disclosure fields have values in Encompass.

WORKFLOW:
1. Use check_required_fields(loan_id) to check all fields at once
2. For specific fields, use get_field_value(loan_id, field_id)
3. To check fields by document type, use get_fields_by_document_type(loan_id, document_type)

REPORT SUMMARY INCLUDING:
- Total fields checked
- Number of fields with values
- Number of fields missing
- List of missing field IDs and names
- Critical missing fields (if any)

Be concise and clear in your report.
"""

# Create the verification agent
verification_agent = create_deep_agent(
    agent_type="Disclosure-Verification-SubAgent",
    system_prompt=verification_instructions,
    tools=[
        check_required_fields,
        get_field_value,
        get_fields_by_document_type
    ]
)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_verification(loan_id: str) -> Dict[str, Any]:
    """Run disclosure verification for a loan.
    
    This function orchestrates the verification process by invoking the
    LangChain agent to check all required fields.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with verification results:
        - loan_id: Loan GUID
        - status: "success" or "failed"
        - fields_checked: Total fields checked
        - fields_with_values: List of field IDs with values
        - fields_missing: List of field IDs missing values
        - field_details: Detailed status for each field
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE VERIFICATION STARTING")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    
    try:
        # Create task for agent
        task = f"""Check all required disclosure fields for loan {loan_id}.

Use check_required_fields() to get the complete status of all fields.

Provide a clear summary including:
1. Total number of fields checked
2. Number of fields with values
3. Number of fields missing
4. List the missing field IDs and names (up to first 10)
5. Assess if any critical fields are missing
"""
        
        # Invoke agent
        result = verification_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Extract results from agent messages
        # The agent will have called check_required_fields, so we extract that
        tool_results = {}
        for message in result["messages"]:
            if hasattr(message, "name") and message.name == "check_required_fields":
                import json
                tool_results = json.loads(message.content)
                break
        
        # Generate summary
        fields_checked = tool_results.get("fields_checked", 0)
        fields_with_values = tool_results.get("fields_with_values", [])
        fields_missing = tool_results.get("fields_missing", [])
        
        summary = f"""Verification Complete:
- Fields checked: {fields_checked}
- Fields with values: {len(fields_with_values)}
- Fields missing: {len(fields_missing)}

Missing fields require attention before disclosure.
"""
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE VERIFICATION COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "fields_checked": fields_checked,
            "fields_with_values": fields_with_values,
            "fields_missing": fields_missing,
            "field_details": tool_results.get("field_details", {}),
            "summary": summary,
            "agent_messages": result["messages"]
        }
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {
            "loan_id": loan_id,
            "status": "failed",
            "error": str(e),
            "fields_checked": 0,
            "fields_with_values": [],
            "fields_missing": []
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Verification Sub-Agent")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID to verify")
    
    args = parser.parse_args()
    
    result = run_disclosure_verification(args.loan_id)
    
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Fields Checked: {result.get('fields_checked', 0)}")
    print(f"Fields With Values: {len(result.get('fields_with_values', []))}")
    print(f"Fields Missing: {len(result.get('fields_missing', []))}")
    
    if result.get('fields_missing'):
        print("\nMissing Fields (first 10):")
        for field_id in result['fields_missing'][:10]:
            field_info = result['field_details'].get(field_id, {})
            field_name = field_info.get('name', 'Unknown')
            print(f"  - {field_id}: {field_name}")
    
    print("\n" + result.get('summary', ''))

