"""Send Sub-Agent for compliance checks and disclosure ordering.

v2: Replaces Request Agent with expanded responsibilities:
- Run Mavent compliance check (MANDATORY)
- Run ATR/QM check (MANDATORY)
- Order eDisclosures via API
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

# Import Mavent tools
from agents.disclosure.subagents.send_agent.tools.mavent_tools import (
    check_mavent,
    get_mavent_issues,
)

# Import ATR/QM tools
from agents.disclosure.subagents.send_agent.tools.atr_qm_tools import (
    check_atr_qm,
    get_points_and_fees_test,
)

# Import Order tools
from agents.disclosure.subagents.send_agent.tools.order_tools import (
    audit_loan,
    order_disclosure_package,
    get_application_id,
)

# Import shared utilities
from packages.shared import (
    read_fields,
    get_loan_summary,
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

send_instructions = """You are the Disclosure Send Agent.

Your job is to run compliance checks and order Initial Disclosures via eDisclosures.

MANDATORY CHECKS (must pass to proceed):
1. Mavent Compliance - All Fail/Alert/Warning must be cleared
2. ATR/QM Flags - All flags must NOT be RED

WORKFLOW:

1. MAVENT COMPLIANCE CHECK (MANDATORY):
   - Use check_mavent(loan_id) to run compliance check
   - If any issues exist (fails, alerts, warnings), DO NOT PROCEED
   - Report all issues and recommend clearing them before retry

2. ATR/QM FLAG CHECK (MANDATORY):
   - Use check_atr_qm(loan_id) to check flag status
   - If any RED flags, DO NOT PROCEED
   - YELLOW flags are warnings but don't block
   - Use get_points_and_fees_test() for detailed Points & Fees info

3. ORDER DISCLOSURES (only if checks pass):
   - Use audit_loan(loan_id) to run mandatory audit
   - If audit passes, use order_disclosure_package(loan_id, dry_run=True/False)
   - Report tracking ID on success

BLOCKING CONDITIONS:
- Mavent has any Fail/Alert/Warning → BLOCK
- ATR/QM has any RED flag → BLOCK
- Audit has unresolved issues → BLOCK

Report your findings clearly:
- Mavent result (passed/failed, issue counts)
- ATR/QM result (all flags, any red/yellow)
- Order result (tracking ID if ordered)
- Any blocking issues that need attention
"""

# Create the send agent
send_agent = create_deep_agent(
    agent_type="Disclosure-Send-SubAgent-v2",
    system_prompt=send_instructions,
    tools=[
        # Mavent Tools
        check_mavent,
        get_mavent_issues,
        # ATR/QM Tools
        check_atr_qm,
        get_points_and_fees_test,
        # Order Tools
        audit_loan,
        order_disclosure_package,
        get_application_id,
    ]
)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_send(
    loan_id: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Run disclosure send workflow.
    
    v2 workflow:
    1. Check Mavent compliance (MANDATORY)
    2. Check ATR/QM flags (MANDATORY)
    3. Order eDisclosures (if checks pass)
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only run checks without ordering
        
    Returns:
        Dictionary with send results:
        - loan_id: Loan GUID
        - status: "success", "blocked", or "failed"
        - mavent_result: Mavent compliance result
        - atr_qm_result: ATR/QM flag result
        - order_result: Order result (if ordered)
        - tracking_id: Disclosure tracking ID (if ordered)
        - blocking_issues: List of issues that blocked sending
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE SEND STARTING (v2)")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"Dry run: {dry_run}")
    
    try:
        # Build task description
        task_parts = [f"Run compliance checks and order disclosures for loan {loan_id}."]
        task_parts.append(f"\nDry run: {dry_run}")
        
        # Step 1: Mavent
        task_parts.append("\n\n=== STEP 1: MAVENT COMPLIANCE (MANDATORY) ===")
        task_parts.append("1. Use check_mavent(loan_id) to run compliance check")
        task_parts.append("2. If ANY issues exist (fails, alerts, warnings), stop and report")
        
        # Step 2: ATR/QM
        task_parts.append("\n\n=== STEP 2: ATR/QM FLAGS (MANDATORY) ===")
        task_parts.append("1. Use check_atr_qm(loan_id) to check all flags")
        task_parts.append("2. If ANY RED flags, stop and report")
        
        # Step 3: Order
        task_parts.append("\n\n=== STEP 3: ORDER DISCLOSURE ===")
        if dry_run:
            task_parts.append("1. Use audit_loan(loan_id) to run audit")
            task_parts.append("2. Report audit results (DRY RUN - do not order)")
        else:
            task_parts.append("1. Use order_disclosure_package(loan_id, dry_run=False) to order")
            task_parts.append("2. Report tracking ID on success")
        
        task_parts.append("\n\nProvide a clear summary of all checks and actions.")
        
        task = "\n".join(task_parts)
        
        # Invoke agent
        logger.info("Invoking AI agent for disclosure send...")
        result = send_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Parse results from agent actions
        import json
        
        mavent_result = None
        atr_qm_result = None
        order_result = None
        blocking_issues = []
        
        for message in result["messages"]:
            if hasattr(message, "name"):
                try:
                    content = json.loads(message.content) if message.content else {}
                    
                    if message.name == "check_mavent":
                        mavent_result = content
                        if not content.get("passed"):
                            total = content.get("total_issues", 0)
                            blocking_issues.append(f"Mavent: {total} compliance issues")
                        
                    elif message.name == "check_atr_qm":
                        atr_qm_result = content
                        if not content.get("passed"):
                            red = content.get("red_flags", [])
                            blocking_issues.append(f"ATR/QM: Red flags - {red}")
                        
                    elif message.name == "order_disclosure_package":
                        order_result = content
                        
                except Exception as e:
                    logger.debug(f"Could not parse message: {e}")
        
        # Determine status
        if blocking_issues:
            status = "blocked"
        elif order_result and order_result.get("success"):
            status = "success"
        else:
            status = "success" if dry_run else "failed"
        
        # Generate summary
        summary_lines = ["Send Complete (v2):"]
        
        # Mavent
        if mavent_result:
            if mavent_result.get("passed"):
                summary_lines.append("✓ Mavent: PASSED - no compliance issues")
            else:
                total = mavent_result.get("total_issues", 0)
                summary_lines.append(f"✗ Mavent: FAILED - {total} issues - BLOCKING")
        
        # ATR/QM
        if atr_qm_result:
            if atr_qm_result.get("passed"):
                summary_lines.append("✓ ATR/QM: All flags acceptable")
            else:
                red = atr_qm_result.get("red_flags", [])
                summary_lines.append(f"✗ ATR/QM: Red flags {red} - BLOCKING")
        
        # Order
        if order_result:
            if order_result.get("success"):
                tracking = order_result.get("tracking_id", "N/A")
                summary_lines.append(f"✓ Order: Success! Tracking ID: {tracking}")
            else:
                summary_lines.append(f"✗ Order: {order_result.get('error', 'Failed')}")
        elif dry_run:
            summary_lines.append("• Order: [DRY RUN - audit only]")
        
        # Blocking
        if blocking_issues:
            summary_lines.append("\n⚠️ BLOCKING ISSUES:")
            for issue in blocking_issues:
                summary_lines.append(f"  - {issue}")
        
        summary = "\n".join(summary_lines)
        
        logger.info("=" * 80)
        logger.info(f"DISCLOSURE SEND COMPLETE - Status: {status.upper()}")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": status,
            "mavent_result": mavent_result,
            "atr_qm_result": atr_qm_result,
            "order_result": order_result,
            "tracking_id": order_result.get("tracking_id") if order_result else None,
            "blocking_issues": blocking_issues,
            "summary": summary,
            "dry_run": dry_run,
            "agent_messages": result["messages"]
        }
        
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return {
            "loan_id": loan_id,
            "status": "failed",
            "error": str(e),
            "mavent_result": None,
            "atr_qm_result": None,
            "order_result": None,
            "tracking_id": None,
            "blocking_issues": [str(e)],
            "dry_run": dry_run
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Send Sub-Agent (v2)")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID to process")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode")
    parser.add_argument("--order", action="store_true", help="Actually order disclosures (not dry run)")
    
    args = parser.parse_args()
    
    dry_run = not args.order
    
    result = run_disclosure_send(
        loan_id=args.loan_id,
        dry_run=dry_run
    )
    
    print("\n" + "=" * 80)
    print("SEND RESULTS (v2)")
    print("=" * 80)
    print(f"Status: {result['status']}")
    
    if result.get('mavent_result'):
        mv = result['mavent_result']
        print(f"\nMavent:")
        print(f"  - Passed: {mv.get('passed')}")
        print(f"  - Issues: {mv.get('total_issues', 0)}")
    
    if result.get('atr_qm_result'):
        aq = result['atr_qm_result']
        print(f"\nATR/QM:")
        print(f"  - Passed: {aq.get('passed')}")
        print(f"  - Red Flags: {aq.get('red_flags', [])}")
    
    if result.get('order_result'):
        order = result['order_result']
        print(f"\nOrder:")
        print(f"  - Success: {order.get('success')}")
        print(f"  - Tracking ID: {order.get('tracking_id')}")
    
    if result.get('blocking_issues'):
        print(f"\n⚠️ Blocking Issues:")
        for issue in result['blocking_issues']:
            print(f"  - {issue}")
    
    print("\n" + result.get('summary', ''))

