"""Preparation Sub-Agent for disclosure field population and cleaning.

This agent uses AI-based field derivation (no hardcoded rules) to populate missing
fields by intelligently searching and reasoning about field relationships.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from copilotagent import create_deep_agent
from agents.disclosure.subagents.preparation_agent.tools.field_derivation_tools import (
    get_loan_field_value,
    search_loan_fields,
    write_field_value,
    get_multiple_field_values
)
from agents.disclosure.subagents.preparation_agent.tools.field_normalization_tools import (
    normalize_phone_number,
    normalize_date,
    normalize_ssn,
    normalize_currency,
    clean_field_value,
    normalize_address
)

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

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

preparation_instructions = """You are a Disclosure Preparation Sub-Agent.

Your job is to populate missing fields and clean existing values using AI-based reasoning.

FOR EACH MISSING FIELD:
1. Use search_loan_fields(loan_id, search_term) to find related fields
   Example: If "Borrower Email" is missing, search for "email"
2. Use get_loan_field_value(loan_id, field_id) to read candidate values
3. Intelligently determine the correct value using reasoning
4. Use write_field_value(loan_id, field_id, value, dry_run=True) to populate

FOR EXISTING FIELDS WITH VALUES:
1. Identify the field type (phone, date, SSN, currency, etc.)
2. Use clean_field_value(field_id, value, field_type) to normalize

STRATEGY - NO HARDCODED RULES:
- Use your reasoning to figure out field relationships
- If a field is missing, think about what related fields might exist
- Search intelligently based on field names and patterns
- Be creative in finding values from related fields

Example workflow for missing "Borrower Email":
1. search_loan_fields(loan_id, "email") to find all email fields
2. Look through results to find populated email fields
3. If you find "Contact Email" or "Primary Email", that's likely the borrower's email
4. Copy that value to the missing "Borrower Email" field

Be thorough but efficient. Report your reasoning for each action.
"""

# Create the preparation agent
preparation_agent = create_deep_agent(
    agent_type="Disclosure-Preparation-SubAgent",
    system_prompt=preparation_instructions,
    tools=[
        get_loan_field_value,
        search_loan_fields,
        write_field_value,
        get_multiple_field_values,
        normalize_phone_number,
        normalize_date,
        normalize_ssn,
        normalize_currency,
        clean_field_value,
        normalize_address
    ]
)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_preparation(
    loan_id: str,
    missing_fields: List[str],
    fields_to_clean: List[Dict[str, Any]] = None,
    demo_mode: bool = True
) -> Dict[str, Any]:
    """Run disclosure preparation for a loan.
    
    This function uses an AI agent to intelligently populate missing fields
    and clean existing values.
    
    Args:
        loan_id: Encompass loan GUID
        missing_fields: List of field IDs that are missing values
        fields_to_clean: List of field dicts with id, value, type to clean
        demo_mode: If True, run in dry-run mode (no actual writes)
        
    Returns:
        Dictionary with preparation results:
        - loan_id: Loan GUID
        - status: "success" or "failed"
        - fields_populated: List of field IDs successfully populated
        - fields_cleaned: List of field IDs successfully cleaned
        - fields_failed: List of field IDs that failed
        - actions: List of actions taken
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE PREPARATION STARTING")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"Missing fields: {len(missing_fields)}")
    logger.info(f"Fields to clean: {len(fields_to_clean or [])}")
    logger.info(f"Demo mode: {demo_mode}")
    
    try:
        # Build task description
        task_parts = [f"Prepare disclosure fields for loan {loan_id}."]
        
        if missing_fields:
            task_parts.append(f"\nMISSING FIELDS TO POPULATE ({len(missing_fields)}):")
            for i, field_id in enumerate(missing_fields[:10], 1):  # Show first 10
                task_parts.append(f"{i}. Field ID: {field_id}")
            if len(missing_fields) > 10:
                task_parts.append(f"... and {len(missing_fields) - 10} more")
            
            task_parts.append("\nFor each missing field:")
            task_parts.append("1. Use search_loan_fields() to find related fields")
            task_parts.append("2. Use get_loan_field_value() to read candidate values")
            task_parts.append("3. Intelligently determine the correct value")
            task_parts.append(f"4. Use write_field_value() with dry_run={demo_mode}")
        
        if fields_to_clean:
            task_parts.append(f"\nFIELDS TO CLEAN/NORMALIZE ({len(fields_to_clean)}):")
            for i, field_info in enumerate(fields_to_clean[:10], 1):
                task_parts.append(f"{i}. Field {field_info.get('id')}: {field_info.get('value')}")
            
            task_parts.append("\nFor each field, use clean_field_value() with appropriate type.")
        
        task_parts.append(f"\nDEMO MODE: {demo_mode} (no actual writes)" if demo_mode else "\nWriting changes to Encompass")
        
        task = "\n".join(task_parts)
        
        # Invoke agent
        logger.info("Invoking AI agent for field preparation...")
        result = preparation_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Parse results from agent actions
        fields_populated = []
        fields_cleaned = []
        fields_failed = []
        actions = []
        
        for message in result["messages"]:
            if hasattr(message, "name"):
                if message.name == "write_field_value":
                    # Field was populated
                    try:
                        import json
                        result_data = json.loads(message.content)
                        if result_data.get("success"):
                            field_id = result_data.get("field_id")
                            fields_populated.append(field_id)
                            actions.append({
                                "action": "populate",
                                "field_id": field_id,
                                "value": result_data.get("value")
                            })
                        else:
                            fields_failed.append(result_data.get("field_id"))
                    except:
                        pass
                        
                elif message.name == "clean_field_value":
                    # Field was cleaned
                    try:
                        field_id = message.content.split()[0] if message.content else "unknown"
                        fields_cleaned.append(field_id)
                        actions.append({
                            "action": "clean",
                            "field_id": field_id
                        })
                    except:
                        pass
        
        # Generate summary
        summary = f"""Preparation Complete:
- Fields populated: {len(fields_populated)}
- Fields cleaned: {len(fields_cleaned)}
- Fields failed: {len(fields_failed)}

Total actions taken: {len(actions)}
"""
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE PREPARATION COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "fields_populated": fields_populated,
            "fields_cleaned": fields_cleaned,
            "fields_failed": fields_failed,
            "actions": actions,
            "summary": summary,
            "demo_mode": demo_mode,
            "agent_messages": result["messages"]
        }
        
    except Exception as e:
        logger.error(f"Preparation failed: {e}")
        return {
            "loan_id": loan_id,
            "status": "failed",
            "error": str(e),
            "fields_populated": [],
            "fields_cleaned": [],
            "fields_failed": []
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Preparation Sub-Agent")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID to prepare")
    parser.add_argument("--missing-fields", type=str, help="Comma-separated field IDs to populate")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (dry run)")
    
    args = parser.parse_args()
    
    missing = args.missing_fields.split(',') if args.missing_fields else []
    
    result = run_disclosure_preparation(
        loan_id=args.loan_id,
        missing_fields=missing,
        demo_mode=args.demo
    )
    
    print("\n" + "=" * 80)
    print("PREPARATION RESULTS")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Fields Populated: {len(result.get('fields_populated', []))}")
    print(f"Fields Cleaned: {len(result.get('fields_cleaned', []))}")
    print(f"Fields Failed: {len(result.get('fields_failed', []))}")
    
    print("\n" + result.get('summary', ''))

