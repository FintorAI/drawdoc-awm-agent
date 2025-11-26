"""Request Sub-Agent for sending disclosures to LOs.

This agent sends email notifications to loan officers with disclosure status summaries.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from copilotagent import create_deep_agent
from agents.disclosure.subagents.request_agent.tools.email_tools import (
    send_disclosure_email,
    get_lo_contact_info
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

request_instructions = """You are a Disclosure Request Sub-Agent.

Your job is to send disclosure review notifications to loan officers via email.

WORKFLOW:
1. Check if all required fields are ready (review verification and preparation results)
2. If LO email not provided, use get_lo_contact_info(loan_id) to find it
3. Use send_disclosure_email() to send notification with field status summary
4. Return confirmation of email sent

IMPORTANT:
- Always include field status summary in email
- Warn LO if critical fields are still missing
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
    
    This function sends an email notification to the loan officer with a
    summary of the disclosure field status.
    
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
        - timestamp: When email was sent
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE REQUEST STARTING")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"LO Email: {lo_email}")
    logger.info(f"Demo mode: {demo_mode}")
    
    try:
        # Build field status summary
        fields_status = {
            "fields_checked": verification_results.get("fields_checked", 0),
            "fields_missing": verification_results.get("fields_missing", []),
            "fields_populated": preparation_results.get("fields_populated", []),
            "fields_cleaned": preparation_results.get("fields_cleaned", [])
        }
        
        missing_count = len(fields_status["fields_missing"])
        populated_count = len(fields_status["fields_populated"])
        ready_for_review = missing_count == 0
        
        # Create task for agent
        task = f"""Send disclosure review notification for loan {loan_id} to {lo_email}.

Field Status Summary:
- Fields checked: {fields_status['fields_checked']}
- Fields missing: {missing_count}
- Fields populated by prep: {populated_count}
- Ready for LO review: {ready_for_review}

Use send_disclosure_email() with:
- loan_id: {loan_id}
- lo_email: {lo_email}
- fields_status: {fields_status}
- dry_run: {demo_mode}

The email should include:
1. Loan ID
2. Field status summary
3. Warning if fields are missing
4. Next steps for LO

Send the email now.
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
        summary = f"""Request Complete:
- Email sent to: {lo_email}
- Fields missing: {missing_count}
- Fields populated: {populated_count}
- Status: {"Ready for review" if ready_for_review else "Missing fields - LO review required"}

{'Email sent successfully.' if email_sent else 'Email send attempted.'}
"""
        
        logger.info("=" * 80)
        logger.info("DISCLOSURE REQUEST COMPLETE")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": "success",
            "email_sent": email_sent,
            "lo_email": lo_email,
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
    
    parser = argparse.ArgumentParser(description="Disclosure Request Sub-Agent")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID")
    parser.add_argument("--lo-email", type=str, required=True, help="LO email address")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (dry run)")
    
    args = parser.parse_args()
    
    # Mock verification and preparation results for testing
    verification_results = {
        "fields_checked": 50,
        "fields_missing": ["FIELD1", "FIELD2"],
        "fields_with_values": []
    }
    
    preparation_results = {
        "fields_populated": ["FIELD1"],
        "fields_cleaned": ["FIELD3", "FIELD4"],
        "fields_failed": ["FIELD2"]
    }
    
    result = run_disclosure_request(
        loan_id=args.loan_id,
        lo_email=args.lo_email,
        verification_results=verification_results,
        preparation_results=preparation_results,
        demo_mode=args.demo
    )
    
    print("\n" + "=" * 80)
    print("REQUEST RESULTS")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Email Sent: {result.get('email_sent', False)}")
    print(f"LO Email: {result.get('lo_email')}")
    
    print("\n" + result.get('summary', ''))

