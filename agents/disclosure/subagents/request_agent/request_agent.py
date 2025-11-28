"""Request Sub-Agent for sending disclosures to LOs.

MVP: Sends email notifications with MI calculation and fee tolerance results.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from copilotagent import create_deep_agent
from agents.disclosure.subagents.request_agent.tools.email_tools import (
    send_disclosure_email,
    get_lo_contact_info
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

request_instructions = """You are a Disclosure Request Sub-Agent.

Your job is to send disclosure review notifications to loan officers via email.

MVP SCOPE:
- Include MI calculation results in email
- Include fee tolerance warnings in email
- Flag non-MVP loans (non-Conventional or non-NV/CA)

WORKFLOW:
1. Check if all required fields are ready
2. Review MI calculation results
3. Review fee tolerance violations (if any)
4. If LO email not provided, use get_lo_contact_info(loan_id) to find it
5. Use send_disclosure_email() to send notification with full summary
6. Return confirmation of email sent

IMPORTANT:
- Always include field status summary in email
- Include MI calculation result (monthly amount if applicable)
- WARN LO if fee tolerance violations exist
- WARN LO if loan is non-MVP (requires manual processing)
- Include loan ID and next steps in email

Be professional and concise in communications.
"""

# Create the request agent
request_agent = create_deep_agent(
    agent_type="Disclosure-Request-SubAgent",
    system_prompt=request_instructions,
    tools=[
        send_disclosure_email,
        get_lo_contact_info
    ]
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_email_summary(
    loan_id: str,
    verification_results: Dict[str, Any],
    preparation_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Build comprehensive email summary with MI and tolerance info.
    
    Args:
        loan_id: Encompass loan GUID
        verification_results: Results from verification agent
        preparation_results: Results from preparation agent
        
    Returns:
        Dictionary with email summary data
    """
    # Basic field status
    fields_checked = verification_results.get("fields_checked", 0)
    fields_missing = verification_results.get("fields_missing", [])
    fields_populated = preparation_results.get("fields_populated", [])
    fields_cleaned = preparation_results.get("fields_cleaned", [])
    
    # MVP status
    is_mvp_supported = verification_results.get("is_mvp_supported", True)
    mvp_warnings = verification_results.get("mvp_warnings", [])
    loan_type = verification_results.get("loan_type", "Unknown")
    property_state = verification_results.get("property_state", "Unknown")
    
    # MI results
    mi_result = preparation_results.get("mi_result", {})
    requires_mi = mi_result.get("requires_mi", False) if mi_result else False
    monthly_mi = mi_result.get("monthly_amount", 0) if mi_result else 0
    mi_source = mi_result.get("source", "N/A") if mi_result else "N/A"
    
    # Tolerance results
    tolerance_result = preparation_results.get("tolerance_result", {})
    has_tolerance_violations = tolerance_result.get("has_violations", False) if tolerance_result else False
    cure_needed = tolerance_result.get("total_cure_needed", 0) if tolerance_result else 0
    
    # Build warnings list
    warnings = []
    if not is_mvp_supported:
        warnings.extend(mvp_warnings)
    if has_tolerance_violations:
        warnings.append(f"Fee tolerance violations found - cure needed: ${cure_needed:.2f}")
    if len(fields_missing) > 0:
        warnings.append(f"{len(fields_missing)} required fields still missing")
    
    # Determine overall status
    ready_for_review = len(fields_missing) == 0 and not has_tolerance_violations
    
    return {
        "loan_id": loan_id,
        "loan_type": loan_type,
        "property_state": property_state,
        "is_mvp_supported": is_mvp_supported,
        "fields_checked": fields_checked,
        "fields_missing_count": len(fields_missing),
        "fields_missing": fields_missing[:10],  # First 10
        "fields_populated_count": len(fields_populated),
        "fields_cleaned_count": len(fields_cleaned),
        "requires_mi": requires_mi,
        "monthly_mi": monthly_mi,
        "mi_source": mi_source,
        "has_tolerance_violations": has_tolerance_violations,
        "tolerance_cure_needed": cure_needed,
        "warnings": warnings,
        "ready_for_review": ready_for_review,
    }


def format_email_body(summary: Dict[str, Any], lo_email: str) -> str:
    """Format email body with all summary information.
    
    Args:
        summary: Email summary dictionary
        lo_email: LO email address
        
    Returns:
        Formatted email body string
    """
    lines = [
        f"Disclosure Review Request",
        f"=" * 40,
        f"",
        f"Loan ID: {summary['loan_id']}",
        f"Loan Type: {summary['loan_type']}",
        f"State: {summary['property_state']}",
        f"",
    ]
    
    # MVP Status
    if not summary['is_mvp_supported']:
        lines.append("⚠️ NON-MVP LOAN - Manual processing may be required")
        lines.append("")
    
    # Field Status
    lines.extend([
        "FIELD STATUS",
        "-" * 20,
        f"Fields Checked: {summary['fields_checked']}",
        f"Fields Missing: {summary['fields_missing_count']}",
        f"Fields Populated: {summary['fields_populated_count']}",
        f"Fields Cleaned: {summary['fields_cleaned_count']}",
        "",
    ])
    
    # MI Status
    lines.append("MORTGAGE INSURANCE")
    lines.append("-" * 20)
    if summary['requires_mi']:
        lines.append(f"MI Required: Yes")
        lines.append(f"Monthly MI: ${summary['monthly_mi']:.2f}")
        lines.append(f"Source: {summary['mi_source']}")
    else:
        lines.append("MI Required: No (LTV ≤ 80%)")
    lines.append("")
    
    # Tolerance Status
    lines.append("FEE TOLERANCE")
    lines.append("-" * 20)
    if summary['has_tolerance_violations']:
        lines.append(f"⚠️ VIOLATIONS FOUND")
        lines.append(f"Cure Needed: ${summary['tolerance_cure_needed']:.2f}")
    else:
        lines.append("No violations")
    lines.append("")
    
    # Warnings
    if summary['warnings']:
        lines.append("WARNINGS")
        lines.append("-" * 20)
        for warning in summary['warnings']:
            lines.append(f"⚠️ {warning}")
        lines.append("")
    
    # Missing Fields
    if summary['fields_missing_count'] > 0:
        lines.append("MISSING FIELDS")
        lines.append("-" * 20)
        for field_id in summary['fields_missing'][:10]:
            lines.append(f"  - {field_id}")
        if summary['fields_missing_count'] > 10:
            lines.append(f"  ... and {summary['fields_missing_count'] - 10} more")
        lines.append("")
    
    # Overall Status
    lines.append("=" * 40)
    if summary['ready_for_review']:
        lines.append("✓ READY FOR LO REVIEW")
    else:
        lines.append("⚠️ ATTENTION REQUIRED - See warnings above")
    lines.append("")
    lines.append("Please review and take appropriate action.")
    
    return "\n".join(lines)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_request(
    loan_id: str,
    lo_email: str,
    verification_results: Dict[str, Any],
    preparation_results: Dict[str, Any],
    demo_mode: bool = True
) -> Dict[str, Any]:
    """Route disclosure to LO for review.
    
    MVP: Includes MI calculation and fee tolerance results in email.
    
    Args:
        loan_id: Encompass loan GUID
        lo_email: Loan officer email address
        verification_results: Results from verification agent
        preparation_results: Results from preparation agent
        demo_mode: If True, run in dry-run mode (no actual email sent)
        
    Returns:
        Dictionary with request results:
        - loan_id: Loan GUID
        - status: "success" or "failed"
        - email_sent: Boolean indicating if email was sent
        - lo_email: LO email address
        - email_summary: Summary data included in email
        - timestamp: When email was sent
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE REQUEST STARTING (MVP)")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"LO Email: {lo_email}")
    logger.info(f"Demo mode: {demo_mode}")
    
    try:
        # Build comprehensive summary
        email_summary = build_email_summary(loan_id, verification_results, preparation_results)
        email_body = format_email_body(email_summary, lo_email)
        
        logger.info(f"[REQUEST] MVP Supported: {email_summary['is_mvp_supported']}")
        logger.info(f"[REQUEST] Requires MI: {email_summary['requires_mi']}")
        logger.info(f"[REQUEST] Tolerance Violations: {email_summary['has_tolerance_violations']}")
        
        # Create task for agent
        task = f"""Send disclosure review notification for loan {loan_id} to {lo_email}.

=== EMAIL CONTENT ===
{email_body}
=====================

Use send_disclosure_email() with:
- loan_id: {loan_id}
- lo_email: {lo_email}
- fields_status: {email_summary}
- dry_run: {demo_mode}

Send the email now with the content above.
"""
        
        # Invoke agent
        logger.info("Invoking AI agent to send disclosure request...")
        result = request_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Extract email send result
        email_sent = False
        email_result = {}
        
        for message in result["messages"]:
            if hasattr(message, "name") and message.name == "send_disclosure_email":
                try:
                    import json
                    email_result = json.loads(message.content)
                    email_sent = email_result.get("success", False)
                    break
                except:
                    pass
        
        # Generate summary
        summary_lines = ["Request Complete (MVP):"]
        summary_lines.append(f"- Email sent to: {lo_email}")
        summary_lines.append(f"- Loan type: {email_summary['loan_type']}")
        summary_lines.append(f"- MVP supported: {email_summary['is_mvp_supported']}")
        
        if email_summary['requires_mi']:
            summary_lines.append(f"- MI Monthly: ${email_summary['monthly_mi']:.2f}")
        else:
            summary_lines.append("- MI: Not required")
        
        if email_summary['has_tolerance_violations']:
            summary_lines.append(f"- ⚠️ Tolerance cure needed: ${email_summary['tolerance_cure_needed']:.2f}")
        
        summary_lines.append(f"- Fields missing: {email_summary['fields_missing_count']}")
        summary_lines.append(f"- Ready for review: {email_summary['ready_for_review']}")
        
        if demo_mode:
            summary_lines.append("\n[DRY RUN - No actual email sent]")
        else:
            summary_lines.append(f"\n{'✓ Email sent successfully.' if email_sent else '⚠️ Email send attempted.'}")
        
        summary = "\n".join(summary_lines)
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE REQUEST COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "email_sent": email_sent,
            "lo_email": lo_email,
            "email_summary": email_summary,
            "email_body": email_body,
            "timestamp": email_result.get("timestamp"),
            "summary": summary,
            "demo_mode": demo_mode,
            "email_result": email_result,
            "agent_messages": result["messages"]
        }
        
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {
            "loan_id": loan_id,
            "status": "failed",
            "error": str(e),
            "email_sent": False,
            "lo_email": lo_email
        }


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Request Sub-Agent (MVP)")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID")
    parser.add_argument("--lo-email", type=str, required=True, help="LO email address")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (dry run)")
    
    args = parser.parse_args()
    
    # Mock verification and preparation results for testing
    verification_results = {
        "fields_checked": 20,
        "fields_missing": ["CD1.X1", "VEND.X263"],
        "fields_with_values": ["1109", "3", "4", "11"],
        "is_mvp_supported": True,
        "mvp_warnings": [],
        "loan_type": "Conventional",
        "property_state": "NV"
    }
    
    preparation_results = {
        "fields_populated": ["CD1.X1"],
        "fields_cleaned": ["4000", "4002"],
        "fields_failed": [],
        "mi_result": {
            "requires_mi": True,
            "monthly_amount": 125.50,
            "source": "calculated",
            "ltv": 85.0
        },
        "tolerance_result": {
            "has_violations": False,
            "total_cure_needed": 0
        }
    }
    
    result = run_disclosure_request(
        loan_id=args.loan_id,
        lo_email=args.lo_email,
        verification_results=verification_results,
        preparation_results=preparation_results,
        demo_mode=args.demo
    )
    
    print("\n" + "=" * 80)
    print("REQUEST RESULTS (MVP)")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Email Sent: {result.get('email_sent', False)}")
    print(f"LO Email: {result.get('lo_email')}")
    
    if result.get('email_summary'):
        summary = result['email_summary']
        print(f"\nLoan Type: {summary.get('loan_type')}")
        print(f"MVP Supported: {summary.get('is_mvp_supported')}")
        print(f"Requires MI: {summary.get('requires_mi')}")
        if summary.get('requires_mi'):
            print(f"Monthly MI: ${summary.get('monthly_mi', 0):.2f}")
        print(f"Tolerance Violations: {summary.get('has_tolerance_violations')}")
    
    print("\n" + result.get('summary', ''))
