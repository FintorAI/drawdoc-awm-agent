"""Verification Sub-Agent for disclosure field checks.

MVP: Checks only ~20 critical fields (not all CSV fields).
This agent checks if required disclosure fields have values in Encompass.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from copilotagent import create_deep_agent
from packages.shared import (
    get_encompass_client,
    read_fields,
    get_loan_type,
    get_loan_summary,
    LoanType,
    PropertyState,
    DISCLOSURE_CRITICAL_FIELDS,
    get_all_critical_field_ids,
    get_field_name,
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
# VERIFICATION TOOLS (using shared utilities)
# =============================================================================

from langchain_core.tools import tool


@tool
def check_critical_fields(loan_id: str) -> dict:
    """Check if critical disclosure fields have values in Encompass.
    
    MVP: Checks only ~20 critical fields instead of all CSV fields.
    This is faster and focuses on what's essential for disclosure.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - fields_checked: Total number of fields checked
        - fields_with_values: List of field IDs that have values
        - fields_missing: List of field IDs that are missing values
        - field_details: Dict mapping field_id to detailed status
        - is_mvp_supported: Whether loan is MVP supported (Conventional, NV/CA)
    """
    logger.info(f"[CHECK] Checking critical fields for loan {loan_id[:8]}...")
    
    # Get loan summary for MVP check
    summary = get_loan_summary(loan_id)
    loan_type = summary.get("loan_type", "Unknown")
    property_state = summary.get("property_state", "Unknown")
    
    # Check MVP support
    is_mvp_loan_type = LoanType.is_mvp_supported(loan_type)
    is_mvp_state = PropertyState.is_mvp_supported(property_state)
    is_mvp_supported = is_mvp_loan_type and is_mvp_state
    
    if not is_mvp_supported:
        logger.warning(f"[CHECK] Non-MVP loan: type={loan_type}, state={property_state}")
    
    # Get all critical field IDs
    field_ids = get_all_critical_field_ids()
    
    logger.info(f"[CHECK] Checking {len(field_ids)} critical fields")
    
    results = {
        "loan_id": loan_id,
        "fields_checked": 0,
        "fields_with_values": [],
        "fields_missing": [],
        "field_details": {},
        "loan_type": loan_type,
        "property_state": property_state,
        "is_mvp_supported": is_mvp_supported,
        "mvp_warnings": [],
    }
    
    # Add MVP warnings
    if not is_mvp_loan_type:
        results["mvp_warnings"].append(f"Non-MVP loan type: {loan_type}. Only Conventional is fully supported.")
    if not is_mvp_state:
        results["mvp_warnings"].append(f"Non-MVP state: {property_state}. Only NV and CA are fully supported.")
    
    # Read all fields at once
    try:
        field_values = read_fields(loan_id, field_ids)
        
        for field_id in field_ids:
            value = field_values.get(field_id)
            has_value = value is not None
            field_name = get_field_name(field_id)
            
            results["fields_checked"] += 1
            results["field_details"][field_id] = {
                "name": field_name,
                "has_value": has_value,
                "value": value if has_value else None
            }
            
            if has_value:
                results["fields_with_values"].append(field_id)
                logger.debug(f"[CHECK] ✓ {field_id} ({field_name}): Has value")
            else:
                results["fields_missing"].append(field_id)
                logger.debug(f"[CHECK] ✗ {field_id} ({field_name}): Missing")
                
    except Exception as e:
        logger.error(f"[CHECK] Error checking fields: {e}")
        results["error"] = str(e)
    
    logger.info(f"[CHECK] Complete - Checked: {results['fields_checked']}, "
                f"With values: {len(results['fields_with_values'])}, "
                f"Missing: {len(results['fields_missing'])}")
    
    return results


@tool
def check_field_value(loan_id: str, field_id: str) -> dict:
    """Check a specific field value from Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        field_id: Encompass field ID
        
    Returns:
        Dictionary with field_id, value, has_value status, and field name
    """
    logger.info(f"[CHECK] Getting field {field_id} for loan {loan_id[:8]}...")
    
    try:
        field_values = read_fields(loan_id, [field_id])
        value = field_values.get(field_id)
        has_value = value is not None
        field_name = get_field_name(field_id)
        
        return {
            "field_id": field_id,
            "name": field_name,
            "value": value,
            "has_value": has_value,
            "success": True
        }
    except Exception as e:
        logger.error(f"[CHECK] Error getting field {field_id}: {e}")
        return {
            "field_id": field_id,
            "error": str(e),
            "success": False
        }


@tool
def check_mvp_eligibility(loan_id: str) -> dict:
    """Check if a loan is eligible for MVP processing.
    
    MVP eligibility:
    - Loan type: Conventional only
    - State: NV or CA only
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with MVP eligibility status and details
    """
    logger.info(f"[CHECK] Checking MVP eligibility for loan {loan_id[:8]}...")
    
    try:
        summary = get_loan_summary(loan_id)
        
        loan_type = summary.get("loan_type", "Unknown")
        property_state = summary.get("property_state", "Unknown")
        
        is_mvp_loan_type = LoanType.is_mvp_supported(loan_type)
        is_mvp_state = PropertyState.is_mvp_supported(property_state)
        is_eligible = is_mvp_loan_type and is_mvp_state
        
        result = {
            "loan_id": loan_id,
            "is_eligible": is_eligible,
            "loan_type": loan_type,
            "is_mvp_loan_type": is_mvp_loan_type,
            "property_state": property_state,
            "is_mvp_state": is_mvp_state,
            "success": True,
        }
        
        if not is_eligible:
            reasons = []
            if not is_mvp_loan_type:
                reasons.append(f"Loan type '{loan_type}' not supported (MVP: Conventional only)")
            if not is_mvp_state:
                reasons.append(f"State '{property_state}' not supported (MVP: NV, CA only)")
            result["ineligibility_reasons"] = reasons
            result["action"] = "manual_processing_required"
        
        return result
        
    except Exception as e:
        logger.error(f"[CHECK] Error checking MVP eligibility: {e}")
        return {
            "loan_id": loan_id,
            "is_eligible": False,
            "error": str(e),
            "success": False,
        }


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

verification_instructions = """You are a Disclosure Verification Sub-Agent.

Your job is to check if critical disclosure fields have values in Encompass.

MVP SCOPE:
- Only ~20 critical fields are checked (not all CSV fields)
- Only Conventional loans in NV/CA are fully supported
- Non-MVP loans should be flagged for manual processing

WORKFLOW:
1. First, use check_mvp_eligibility(loan_id) to see if this loan is MVP-eligible
2. Use check_critical_fields(loan_id) to check all critical fields at once
3. For specific fields, use check_field_value(loan_id, field_id)

REPORT SUMMARY INCLUDING:
- MVP eligibility status (is this Conventional in NV/CA?)
- Total fields checked
- Number of fields with values
- Number of fields missing
- List of missing field IDs and names (up to first 10)
- Critical warnings if non-MVP loan type or state

Be concise and clear in your report.
"""

# Create the verification agent
verification_agent = create_deep_agent(
    agent_type="Disclosure-Verification-SubAgent",
    system_prompt=verification_instructions,
    tools=[
        check_critical_fields,
        check_field_value,
        check_mvp_eligibility,
    ]
)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_verification(loan_id: str) -> Dict[str, Any]:
    """Run disclosure verification for a loan.
    
    MVP: Only checks ~20 critical fields and validates MVP eligibility.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with verification results:
        - loan_id: Loan GUID
        - status: "success" or "failed"
        - is_mvp_supported: Whether loan is MVP eligible
        - fields_checked: Total fields checked
        - fields_with_values: List of field IDs with values
        - fields_missing: List of field IDs missing values
        - field_details: Detailed status for each field
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE VERIFICATION STARTING (MVP)")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    
    try:
        # Create task for agent
        task = f"""Verify disclosure fields for loan {loan_id}.

1. First, check if this loan is MVP-eligible using check_mvp_eligibility()
2. Then check all critical fields using check_critical_fields()

Provide a clear summary including:
1. MVP eligibility (Conventional loan in NV/CA?)
2. Total number of critical fields checked
3. Number of fields with values
4. Number of fields missing
5. List the missing field IDs and names (up to first 10)
6. Any warnings about MVP eligibility
"""
        
        # Invoke agent
        result = verification_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Extract results from agent messages
        tool_results = {}
        mvp_eligibility = {}
        
        for message in result["messages"]:
            if hasattr(message, "name"):
                if message.name == "check_critical_fields":
                    import json
                    tool_results = json.loads(message.content)
                elif message.name == "check_mvp_eligibility":
                    import json
                    mvp_eligibility = json.loads(message.content)
        
        # Generate summary
        fields_checked = tool_results.get("fields_checked", 0)
        fields_with_values = tool_results.get("fields_with_values", [])
        fields_missing = tool_results.get("fields_missing", [])
        is_mvp_supported = tool_results.get("is_mvp_supported", True)
        mvp_warnings = tool_results.get("mvp_warnings", [])
        
        summary_lines = ["Verification Complete (MVP):"]
        summary_lines.append(f"- Fields checked: {fields_checked}")
        summary_lines.append(f"- Fields with values: {len(fields_with_values)}")
        summary_lines.append(f"- Fields missing: {len(fields_missing)}")
        
        if not is_mvp_supported:
            summary_lines.append("\n⚠️ NON-MVP LOAN - Manual processing may be required:")
            for warning in mvp_warnings:
                summary_lines.append(f"  - {warning}")
        
        if fields_missing:
            summary_lines.append("\nMissing fields require attention before disclosure.")
        
        summary = "\n".join(summary_lines)
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE VERIFICATION COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "is_mvp_supported": is_mvp_supported,
            "mvp_warnings": mvp_warnings,
            "fields_checked": fields_checked,
            "fields_with_values": fields_with_values,
            "fields_missing": fields_missing,
            "field_details": tool_results.get("field_details", {}),
            "loan_type": tool_results.get("loan_type"),
            "property_state": tool_results.get("property_state"),
            "summary": summary,
            "agent_messages": result["messages"]
        }
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {
            "loan_id": loan_id,
            "status": "failed",
            "error": str(e),
            "is_mvp_supported": False,
            "fields_checked": 0,
            "fields_with_values": [],
            "fields_missing": []
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Verification Sub-Agent (MVP)")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID to verify")
    
    args = parser.parse_args()
    
    result = run_disclosure_verification(args.loan_id)
    
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS (MVP)")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"MVP Supported: {result.get('is_mvp_supported', 'Unknown')}")
    print(f"Loan Type: {result.get('loan_type', 'Unknown')}")
    print(f"State: {result.get('property_state', 'Unknown')}")
    print(f"Fields Checked: {result.get('fields_checked', 0)}")
    print(f"Fields With Values: {len(result.get('fields_with_values', []))}")
    print(f"Fields Missing: {len(result.get('fields_missing', []))}")
    
    if result.get('mvp_warnings'):
        print("\n⚠️ MVP Warnings:")
        for warning in result['mvp_warnings']:
            print(f"  - {warning}")
    
    if result.get('fields_missing'):
        print("\nMissing Fields (first 10):")
        for field_id in result['fields_missing'][:10]:
            field_info = result['field_details'].get(field_id, {})
            field_name = field_info.get('name', 'Unknown')
            print(f"  - {field_id}: {field_name}")
    
    print("\n" + result.get('summary', ''))
