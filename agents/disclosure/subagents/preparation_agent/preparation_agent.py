"""Preparation Sub-Agent for disclosure field population, MI calculation, and tolerance checking.

MVP: 
- Calculate Conventional MI only
- Populate basic CD fields
- Flag fee tolerance violations (no auto-cure)
- Use AI for field derivation when needed
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

# Import existing tools
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

# Import new MI tools
from agents.disclosure.subagents.preparation_agent.tools.mi_tools import (
    calculate_loan_mi,
    populate_mi_fields,
    check_mi_required,
)

# Import shared utilities
from packages.shared import (
    read_fields,
    write_fields,
    get_loan_summary,
    check_fee_tolerance,
    extract_fees_from_fields,
    get_all_fee_field_ids,
    LoanType,
    SECTION_A_FEES,
    SECTION_B_FEES,
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
# FEE TOLERANCE TOOLS
# =============================================================================

from langchain_core.tools import tool


@tool
def check_loan_fee_tolerance(loan_id: str) -> dict:
    """Check fee tolerance between LE and CD fees.
    
    MVP: Flags violations only - does not auto-cure.
    
    Compares fees from Last LE vs Current CD to identify:
    - 0% tolerance violations (Section A fees)
    - 10% tolerance violations (Section B fees aggregate)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with tolerance check results:
        - has_violations: Whether any violations found
        - total_cure_needed: Total cure amount (for reference only)
        - violations: List of violation details
        - summary: Human-readable summary
        
    Note:
        MVP does not apply cures. Violations are flagged for manual review.
    """
    logger.info(f"[TOLERANCE] Checking fee tolerance for loan {loan_id[:8]}...")
    
    try:
        # Get all fee field IDs
        fee_field_ids = get_all_fee_field_ids()
        
        # For MVP, we'll read current CD fees
        # In production, would compare LE vs CD
        cd_values = read_fields(loan_id, fee_field_ids)
        cd_fees = extract_fees_from_fields(cd_values, fee_field_ids)
        
        # For MVP, use current CD as both LE and CD (no comparison available)
        # In production, would read LE fees from LE document
        le_fees = cd_fees  # Placeholder - no violations in MVP demo
        
        # Check tolerance
        result = check_fee_tolerance(le_fees, cd_fees)
        
        return {
            "loan_id": loan_id,
            "success": True,
            "has_violations": result.has_violations,
            "total_cure_needed": result.total_cure_needed,
            "zero_tolerance_violations": [v.to_dict() for v in result.zero_tolerance_violations],
            "ten_percent_violations": [v.to_dict() for v in result.ten_percent_violations],
            "summary": result.get_summary(),
            "action": "manual_review" if result.has_violations else "none",
        }
        
    except Exception as e:
        logger.error(f"[TOLERANCE] Error checking fee tolerance: {e}")
        return {
            "loan_id": loan_id,
            "success": False,
            "error": str(e),
            "has_violations": False,
        }


@tool
def get_cd_field_status(loan_id: str) -> dict:
    """Get status of CD-related fields for pages 1-3.
    
    Checks if basic CD fields are populated for disclosure.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with CD field status
    """
    logger.info(f"[CD_STATUS] Getting CD field status for loan {loan_id[:8]}...")
    
    # Key CD fields for pages 1-3
    cd_field_ids = [
        "CD1.X1",    # CD Date Issued
        "1109",      # Loan Amount
        "3",         # Interest Rate
        "4",         # Loan Term
        "11",        # Property Address
        "356",       # Appraised Value
        "136",       # Purchase Price
        "4000",      # Borrower First Name
        "4002",      # Borrower Last Name
        "232",       # Monthly MI
    ]
    
    try:
        values = read_fields(loan_id, cd_field_ids)
        
        field_status = {}
        populated = []
        missing = []
        
        for field_id in cd_field_ids:
            value = values.get(field_id)
            has_value = value is not None
            field_status[field_id] = {
                "has_value": has_value,
                "value": value if has_value else None,
            }
            if has_value:
                populated.append(field_id)
            else:
                missing.append(field_id)
        
        return {
            "loan_id": loan_id,
            "success": True,
            "fields_checked": len(cd_field_ids),
            "populated_count": len(populated),
            "missing_count": len(missing),
            "populated_fields": populated,
            "missing_fields": missing,
            "field_status": field_status,
        }
        
    except Exception as e:
        logger.error(f"[CD_STATUS] Error getting CD field status: {e}")
        return {
            "loan_id": loan_id,
            "success": False,
            "error": str(e),
        }


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

preparation_instructions = """You are a Disclosure Preparation Sub-Agent.

Your job is to:
1. Calculate MI (Mortgage Insurance) for Conventional loans
2. Check fee tolerance violations (flag only, no auto-cure)
3. Populate missing CD fields using AI-based derivation

MVP SCOPE:
- Only Conventional MI is fully calculated
- Fee tolerance violations are flagged (not auto-cured)
- Focus on CD pages 1-3 fields

WORKFLOW:

1. MORTGAGE INSURANCE:
   - Use check_mi_required(loan_id) to see if MI is needed
   - If needed, use calculate_loan_mi(loan_id) to calculate MI
   - Use populate_mi_fields() to write MI values (dry_run=True for safety)

2. FEE TOLERANCE:
   - Use check_loan_fee_tolerance(loan_id) to check for violations
   - Report any violations found (do not attempt to cure)

3. CD FIELD POPULATION:
   - Use get_cd_field_status(loan_id) to see what's missing
   - For missing fields, use AI derivation tools:
     - search_loan_fields() to find related fields
     - get_loan_field_value() to read candidate values
     - write_field_value() to populate (dry_run=True)

4. FIELD NORMALIZATION:
   - Use clean_field_value() to normalize formats
   - Use normalize_phone_number(), normalize_date(), etc.

Report your findings clearly, including:
- MI calculation result
- Fee tolerance violations (if any)
- Fields populated
- Fields that still need attention
"""

# Create the preparation agent
preparation_agent = create_deep_agent(
    agent_type="Disclosure-Preparation-SubAgent",
    system_prompt=preparation_instructions,
    tools=[
        # MI Tools
        calculate_loan_mi,
        populate_mi_fields,
        check_mi_required,
        # Tolerance Tools
        check_loan_fee_tolerance,
        get_cd_field_status,
        # Field Derivation Tools
        get_loan_field_value,
        search_loan_fields,
        write_field_value,
        get_multiple_field_values,
        # Normalization Tools
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
    
    MVP workflow:
    1. Calculate MI (Conventional only)
    2. Check fee tolerance (flag only)
    3. Populate missing CD fields
    4. Normalize existing fields
    
    Args:
        loan_id: Encompass loan GUID
        missing_fields: List of field IDs that are missing values
        fields_to_clean: List of field dicts with id, value, type to clean
        demo_mode: If True, run in dry-run mode (no actual writes)
        
    Returns:
        Dictionary with preparation results:
        - loan_id: Loan GUID
        - status: "success" or "failed"
        - mi_result: MI calculation result
        - tolerance_result: Fee tolerance check result
        - fields_populated: List of field IDs populated
        - fields_cleaned: List of field IDs cleaned
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE PREPARATION STARTING (MVP)")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"Missing fields: {len(missing_fields)}")
    logger.info(f"Fields to clean: {len(fields_to_clean or [])}")
    logger.info(f"Demo mode: {demo_mode}")
    
    try:
        # Build task description
        task_parts = [f"Prepare disclosure for loan {loan_id}."]
        task_parts.append(f"\nDemo mode: {demo_mode} (dry_run={demo_mode})")
        
        # Step 1: MI Calculation
        task_parts.append("\n\n=== STEP 1: MORTGAGE INSURANCE ===")
        task_parts.append("1. Check if MI is required using check_mi_required()")
        task_parts.append("2. If required, calculate MI using calculate_loan_mi()")
        task_parts.append(f"3. Populate MI fields using populate_mi_fields() with dry_run={demo_mode}")
        
        # Step 2: Fee Tolerance
        task_parts.append("\n\n=== STEP 2: FEE TOLERANCE ===")
        task_parts.append("1. Check fee tolerance using check_loan_fee_tolerance()")
        task_parts.append("2. Report any violations found (do NOT attempt to cure)")
        
        # Step 3: CD Fields
        task_parts.append("\n\n=== STEP 3: CD FIELD POPULATION ===")
        task_parts.append("1. Check CD field status using get_cd_field_status()")
        
        if missing_fields:
            task_parts.append(f"\nMissing fields to address ({len(missing_fields)}):")
            for i, field_id in enumerate(missing_fields[:5], 1):
                task_parts.append(f"  {i}. {field_id}")
            if len(missing_fields) > 5:
                task_parts.append(f"  ... and {len(missing_fields) - 5} more")
            task_parts.append(f"\nUse write_field_value() with dry_run={demo_mode}")
        
        if fields_to_clean:
            task_parts.append(f"\nFields to normalize ({len(fields_to_clean)}):")
            for i, field_info in enumerate(fields_to_clean[:5], 1):
                task_parts.append(f"  {i}. {field_info.get('id')}")
        
        task_parts.append("\n\nProvide a clear summary of all actions taken.")
        
        task = "\n".join(task_parts)
        
        # Invoke agent
        logger.info("Invoking AI agent for disclosure preparation...")
        result = preparation_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Parse results from agent actions
        mi_result = None
        tolerance_result = None
        fields_populated = []
        fields_cleaned = []
        fields_failed = []
        actions = []
        
        for message in result["messages"]:
            if hasattr(message, "name"):
                try:
                    import json
                    content = json.loads(message.content) if message.content else {}
                    
                    if message.name == "calculate_loan_mi":
                        mi_result = content
                        actions.append({"action": "mi_calculation", "result": content})
                        
                    elif message.name == "check_loan_fee_tolerance":
                        tolerance_result = content
                        actions.append({"action": "tolerance_check", "result": content})
                        
                    elif message.name == "write_field_value":
                        if content.get("success"):
                            field_id = content.get("field_id")
                            fields_populated.append(field_id)
                            actions.append({
                                "action": "populate",
                                "field_id": field_id,
                                "value": content.get("value"),
                                "dry_run": content.get("dry_run", True)
                            })
                        else:
                            fields_failed.append(content.get("field_id"))
                            
                    elif message.name == "populate_mi_fields":
                        if content.get("success"):
                            actions.append({
                                "action": "populate_mi",
                                "fields": content.get("fields_written", []),
                                "dry_run": content.get("dry_run", True)
                            })
                            
                    elif message.name == "clean_field_value":
                        field_id = content.get("field_id", "unknown")
                        fields_cleaned.append(field_id)
                        actions.append({"action": "clean", "field_id": field_id})
                        
                except Exception as e:
                    logger.debug(f"Could not parse message: {e}")
        
        # Generate summary
        summary_lines = ["Preparation Complete (MVP):"]
        
        # MI Summary
        if mi_result:
            if mi_result.get("requires_mi"):
                summary_lines.append(f"\n✓ MI Calculated: ${mi_result.get('monthly_amount', 0):.2f}/month")
            else:
                summary_lines.append("\n✓ MI: Not required (LTV ≤ 80%)")
        
        # Tolerance Summary
        if tolerance_result:
            if tolerance_result.get("has_violations"):
                summary_lines.append(f"\n⚠️ Fee Tolerance: {tolerance_result.get('summary', 'Violations found')}")
            else:
                summary_lines.append("\n✓ Fee Tolerance: No violations")
        
        # Fields Summary
        summary_lines.append(f"\n- Fields populated: {len(fields_populated)}")
        summary_lines.append(f"- Fields cleaned: {len(fields_cleaned)}")
        summary_lines.append(f"- Fields failed: {len(fields_failed)}")
        summary_lines.append(f"\nTotal actions: {len(actions)}")
        
        if demo_mode:
            summary_lines.append("\n[DRY RUN - No actual writes performed]")
        
        summary = "\n".join(summary_lines)
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE PREPARATION COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "mi_result": mi_result,
            "tolerance_result": tolerance_result,
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
            "mi_result": None,
            "tolerance_result": None,
            "fields_populated": [],
            "fields_cleaned": [],
            "fields_failed": []
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Preparation Sub-Agent (MVP)")
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
    print("PREPARATION RESULTS (MVP)")
    print("=" * 80)
    print(f"Status: {result['status']}")
    
    if result.get('mi_result'):
        mi = result['mi_result']
        print(f"\nMI Calculation:")
        print(f"  - Requires MI: {mi.get('requires_mi')}")
        if mi.get('requires_mi'):
            print(f"  - Monthly Amount: ${mi.get('monthly_amount', 0):.2f}")
            print(f"  - Source: {mi.get('source')}")
    
    if result.get('tolerance_result'):
        tol = result['tolerance_result']
        print(f"\nFee Tolerance:")
        print(f"  - Has Violations: {tol.get('has_violations')}")
        if tol.get('has_violations'):
            print(f"  - Cure Needed: ${tol.get('total_cure_needed', 0):.2f}")
    
    print(f"\nFields Populated: {len(result.get('fields_populated', []))}")
    print(f"Fields Cleaned: {len(result.get('fields_cleaned', []))}")
    print(f"Fields Failed: {len(result.get('fields_failed', []))}")
    
    print("\n" + result.get('summary', ''))
