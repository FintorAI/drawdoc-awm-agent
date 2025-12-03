"""Verification Sub-Agent for disclosure field checks.

v2: Adds TRID compliance checking and expanded form validation for LE.
This agent validates prerequisites for Initial Loan Estimate (LE) disclosure.
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
    MVPExclusions,
    DISCLOSURE_CRITICAL_FIELDS,
    get_all_critical_field_ids,
    get_field_name,
    # v2 additions
    check_trid_compliance,
    check_lock_status,
    check_closing_date,  # G8: 15-day closing date rule
    validate_disclosure_forms,
    check_hard_stop_fields,  # G1: Phone/Email hard stop
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
    
    MVP eligibility (v2):
    - Loan type: Conventional only (FHA/VA/USDA require manual)
    - State: NOT Texas (TX has special state rules)
    - State: NV or CA preferred, others may work
    
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
        
        # v2: Use MVPExclusions for checking
        is_excluded_loan_type = MVPExclusions.is_excluded_loan_type(loan_type)
        is_excluded_state = MVPExclusions.is_excluded_state(property_state)
        is_mvp_loan_type = not is_excluded_loan_type
        is_mvp_state = not is_excluded_state
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
            if is_excluded_loan_type:
                reasons.append(f"Loan type '{loan_type}' requires manual processing (MVP: Conventional only)")
            if is_excluded_state:
                reasons.append(f"State '{property_state}' has special rules (TX excluded from MVP)")
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


@tool
def check_trid_dates(loan_id: str) -> dict:
    """Check TRID compliance dates for Initial LE disclosure.
    
    Per SOP: LE must be sent within 3 business days of Application Date.
    Business days exclude Sundays and federal holidays.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - compliant: Whether dates are compliant
        - application_date: Application date (ISO format)
        - le_due_date: LE due date (ISO format)
        - days_remaining: Days until LE due date
        - is_past_due: Whether LE due date has passed
        - action: Recommended action if non-compliant
        - blocking: Whether this blocks disclosure
    """
    logger.info(f"[TRID] Checking TRID dates for loan {loan_id[:8]}...")
    
    try:
        result = check_trid_compliance(loan_id)
        
        if result.get("is_past_due"):
            logger.warning(f"[TRID] LE Due Date PASSED - escalate to supervisor")
        elif result.get("compliant"):
            logger.info(f"[TRID] TRID compliant - {result.get('days_remaining', 0)} days remaining")
        else:
            logger.warning(f"[TRID] TRID not compliant: {result.get('action')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRID] Error checking TRID dates: {e}")
        return {
            "compliant": False,
            "error": str(e),
            "blocking": True,
            "action": "Error checking TRID compliance - see error details"
        }


@tool
def check_rate_lock_status(loan_id: str) -> dict:
    """Check rate lock status for the loan.
    
    Per SOP:
    - Case 1 (Locked Loans): All TRID info must be updated
    - Case 2 (Non-Locked Loans): Monitor App Date & LE Due Date
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - is_locked: Whether rate is locked
        - lock_date: Lock date (if locked)
        - lock_expiration: Lock expiration date
        - flow: "locked" or "non_locked"
    """
    logger.info(f"[TRID] Checking lock status for loan {loan_id[:8]}...")
    
    try:
        result = check_lock_status(loan_id)
        
        # Add flow indicator
        result["flow"] = "locked" if result.get("is_locked") else "non_locked"
        
        if result.get("is_locked"):
            logger.info(f"[TRID] Loan is LOCKED - using locked flow")
        else:
            logger.info(f"[TRID] Loan is NOT LOCKED - using non-locked flow")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRID] Error checking lock status: {e}")
        return {
            "is_locked": False,
            "flow": "non_locked",
            "error": str(e)
        }


@tool
def validate_disclosure_form_fields(loan_id: str) -> dict:
    """Validate all required form fields for disclosure.
    
    Per SOP, validates:
    - 1003 URLA Lender Form (all 4 parts)
    - Borrower Summary Origination
    - FACT Act Disclosure (credit scores)
    - RegZ-LE fields
    - Affiliated Business Arrangements
    - LO Info (NMLS verification)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - all_valid: Whether all forms passed validation
        - forms_checked: Number of forms checked
        - forms_passed: Number of forms that passed
        - missing_critical: List of critical missing fields (blocking)
        - missing_fields: List of all missing fields
        - blocking: Whether this blocks disclosure
    """
    logger.info(f"[FORM] Validating all disclosure forms for loan {loan_id[:8]}...")
    
    try:
        result = validate_disclosure_forms(loan_id)
        
        logger.info(f"[FORM] Validation complete: {result.get('forms_passed')}/{result.get('forms_checked')} forms passed")
        
        if result.get("missing_critical"):
            logger.warning(f"[FORM] Missing critical fields: {result.get('missing_critical')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[FORM] Error validating forms: {e}")
        return {
            "all_valid": False,
            "error": str(e),
            "blocking": True,
        }


@tool
def check_closing_date_rule(loan_id: str) -> dict:
    """Check closing date meets 15-day rule (G8).
    
    Per SOP: Closing date must be at least 15 days after:
    - Application date (if loan is NOT locked)
    - Last rate set date (if loan IS locked)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - is_valid: Whether closing date meets requirement
        - closing_date: Estimated closing date
        - reference_date: App date or rate set date used
        - days_until_closing: Days between reference and closing
        - minimum_days: Required minimum (15)
        - blocking: Whether this blocks disclosure
    """
    logger.info(f"[TRID] Checking 15-day closing date rule for loan {loan_id[:8]}...")
    
    try:
        result = check_closing_date(loan_id)
        
        if result.get("is_valid"):
            logger.info(f"[TRID] Closing date valid: {result.get('days_until_closing')} days")
        else:
            logger.warning(f"[TRID] Closing date INVALID: {result.get('action')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TRID] Error checking closing date: {e}")
        return {
            "is_valid": False,
            "error": str(e),
            "blocking": True,
            "action": "Error checking closing date rule"
        }


@tool
def check_hard_stops(loan_id: str) -> dict:
    """Check HARD STOP fields per SOP (G1).
    
    Per SOP: Missing phone number or email is a HARD STOP.
    Disclosure CANNOT proceed if these are missing.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - has_hard_stops: Whether any hard stop fields are missing
        - missing_fields: List of missing hard stop fields
        - blocking: Whether this blocks disclosure
        - blocking_message: Message explaining the hard stop
    """
    logger.info(f"[FORM] Checking HARD STOP fields for loan {loan_id[:8]}...")
    
    try:
        result = check_hard_stop_fields(loan_id)
        
        if result.get("has_hard_stops"):
            logger.error(f"[FORM] HARD STOP: Missing {result.get('missing_fields')}")
        else:
            logger.info(f"[FORM] No hard stops - phone and email present")
        
        return result
        
    except Exception as e:
        logger.error(f"[FORM] Error checking hard stops: {e}")
        return {
            "has_hard_stops": True,
            "missing_fields": ["unknown"],
            "blocking": True,
            "blocking_message": f"Error checking hard stop fields: {e}"
        }


# =============================================================================
# AGENT CONFIGURATION (v2)
# =============================================================================

verification_instructions = """You are the Disclosure Verification Agent.

Your job is to validate prerequisites for Initial Loan Estimate (LE) disclosure.

MVP SCOPE (v2):
- Conventional loans only (FHA/VA/USDA require manual processing)
- NOT Texas (TX has special state rules)
- Focus on LE (Loan Estimate), not CD (Closing Disclosure)

WORKFLOW:
1. Check TRID compliance FIRST (app date, LE due date) using check_trid_dates()
2. Check HARD STOPS (phone/email) using check_hard_stops() - G1
3. Check closing date 15-day rule using check_closing_date_rule() - G8
4. Check if loan is MVP-eligible using check_mvp_eligibility()
5. Check lock status using check_rate_lock_status()
6. Validate required form fields using validate_disclosure_form_fields()
7. Check critical fields using check_critical_fields()

BLOCKING CONDITIONS (must halt and report):
- Application Date not set
- LE Due Date has passed → Escalate to Supervisor
- Missing Phone or Email → HARD STOP (G1)
- Closing date < 15 days from app date → Must adjust (G8)
- Texas property → Manual processing required
- Non-Conventional loan → Manual processing required
- Critical form fields missing

REPORT SUMMARY INCLUDING:
- TRID compliance (app date, LE due date, days remaining)
- HARD STOP status (phone/email present?) - G1
- Closing date validity (15-day rule met?) - G8
- MVP eligibility status (Conventional? Not TX?)
- Lock status (locked vs non-locked flow)
- Form validation results (critical fields missing?)
- Any blocking conditions that require attention

Be concise and clear in your report.
"""

# Create the verification agent
verification_agent = create_deep_agent(
    agent_type="Disclosure-Verification-SubAgent-v2",
    system_prompt=verification_instructions,
    tools=[
        # TRID tools (v2)
        check_trid_dates,
        check_rate_lock_status,
        check_closing_date_rule,  # G8: 15-day rule
        # Form validation (v2)
        validate_disclosure_form_fields,
        check_hard_stops,  # G1: Phone/Email hard stop
        # Original tools
        check_critical_fields,
        check_field_value,
        check_mvp_eligibility,
    ]
)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_disclosure_verification(loan_id: str) -> Dict[str, Any]:
    """Run disclosure verification for a loan (v2).
    
    v2 additions:
    - TRID compliance checking (app date, LE due date)
    - Lock status checking
    - Expanded form validation
    - Focus on LE instead of CD
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with verification results:
        - loan_id: Loan GUID
        - status: "success", "blocked", or "failed"
        - is_mvp_supported: Whether loan is MVP eligible
        - trid_compliance: TRID check results (v2)
        - lock_status: Lock status results (v2)
        - form_validation: Form validation results (v2)
        - fields_checked: Total fields checked
        - fields_missing: List of field IDs missing values
        - blocking_issues: List of issues that block disclosure
        - summary: Human-readable summary
    """
    from langchain_core.messages import HumanMessage
    
    logger.info("=" * 80)
    logger.info("DISCLOSURE VERIFICATION STARTING (v2 - LE Focus)")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    
    try:
        # Create task for agent (v2 workflow with G1/G8)
        task = f"""Verify Initial Loan Estimate (LE) disclosure prerequisites for loan {loan_id}.

WORKFLOW:
1. First, check TRID compliance using check_trid_dates()
2. Check HARD STOPS (phone/email) using check_hard_stops() - G1
3. Check closing date 15-day rule using check_closing_date_rule() - G8
4. Check MVP eligibility using check_mvp_eligibility()
5. Check lock status using check_rate_lock_status()
6. Validate form fields using validate_disclosure_form_fields()
7. Check critical fields using check_critical_fields()

Report any BLOCKING issues:
- Application Date not set
- LE Due Date has passed
- Missing Phone/Email (HARD STOP - G1)
- Closing date < 15 days from app date (G8)
- Texas property
- Non-Conventional loan
- Critical fields missing

Provide a clear summary of all results.
"""
        
        # Invoke agent
        result = verification_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        # Extract results from agent messages
        import json
        
        trid_result = {}
        lock_result = {}
        form_result = {}
        field_result = {}
        mvp_result = {}
        hard_stop_result = {}  # G1
        closing_date_result = {}  # G8
        
        for message in result["messages"]:
            if hasattr(message, "name"):
                try:
                    content = json.loads(message.content)
                    if message.name == "check_trid_dates":
                        trid_result = content
                    elif message.name == "check_rate_lock_status":
                        lock_result = content
                    elif message.name == "validate_disclosure_form_fields":
                        form_result = content
                    elif message.name == "check_critical_fields":
                        field_result = content
                    elif message.name == "check_mvp_eligibility":
                        mvp_result = content
                    elif message.name == "check_hard_stops":
                        hard_stop_result = content  # G1
                    elif message.name == "check_closing_date_rule":
                        closing_date_result = content  # G8
                except:
                    pass
        
        # Collect blocking issues
        blocking_issues = []
        
        if trid_result.get("is_past_due"):
            blocking_issues.append("LE Due Date has PASSED - Escalate to Supervisor")
        if not trid_result.get("application_date"):
            blocking_issues.append("Application Date not set")
        
        # G1: Hard stops
        if hard_stop_result.get("has_hard_stops"):
            missing = hard_stop_result.get("missing_fields", [])
            blocking_issues.append(f"HARD STOP: Missing {', '.join(missing)} - Cannot proceed")
        
        # G8: Closing date rule
        if closing_date_result and not closing_date_result.get("is_valid", True):
            blocking_issues.append(f"Closing date invalid: {closing_date_result.get('action', 'Less than 15 days')}")
        
        if not mvp_result.get("is_eligible", True):
            for reason in mvp_result.get("ineligibility_reasons", []):
                blocking_issues.append(reason)
        
        if form_result.get("missing_critical"):
            blocking_issues.append(f"Critical fields missing: {form_result.get('missing_critical')}")
        
        # G1: Also check hard stops from form validation (fallback)
        if form_result.get("has_hard_stops"):
            blocking_issues.append(f"HARD STOP: Missing {form_result.get('hard_stop_fields', [])}")
        
        # Determine status
        if blocking_issues:
            status = "blocked"
        else:
            status = "success"
        
        # Generate summary
        is_mvp_supported = mvp_result.get("is_eligible", True)
        fields_checked = field_result.get("fields_checked", 0)
        fields_missing = field_result.get("fields_missing", [])
        
        summary_lines = ["Verification Complete (v2 - LE Focus):"]
        
        # TRID
        if trid_result.get("compliant"):
            summary_lines.append(f"✓ TRID: Compliant ({trid_result.get('days_remaining', 0)} days until LE due)")
        elif trid_result.get("is_past_due"):
            summary_lines.append(f"✗ TRID: LE Due Date PASSED - BLOCKING")
        else:
            summary_lines.append(f"✗ TRID: {trid_result.get('action', 'Issue detected')}")
        
        # G1: Hard stops
        if hard_stop_result.get("has_hard_stops"):
            summary_lines.append(f"✗ HARD STOP: Missing {hard_stop_result.get('missing_fields', [])} - BLOCKING")
        else:
            summary_lines.append(f"✓ Hard Stops: Phone & Email present")
        
        # G8: Closing date
        if closing_date_result:
            if closing_date_result.get("is_valid"):
                days = closing_date_result.get("days_until_closing", 0)
                summary_lines.append(f"✓ Closing Date: Valid ({days} days from ref date)")
            else:
                summary_lines.append(f"✗ Closing Date: {closing_date_result.get('action', 'Invalid')} - BLOCKING")
        
        # Lock status
        flow = lock_result.get("flow", "unknown")
        summary_lines.append(f"• Lock Status: {flow.upper()}")
        
        # MVP
        if is_mvp_supported:
            summary_lines.append(f"✓ MVP Eligible: Yes")
        else:
            summary_lines.append(f"✗ MVP Eligible: No - {mvp_result.get('ineligibility_reasons', [])}")
        
        # Forms
        forms_passed = form_result.get("forms_passed", 0)
        forms_checked = form_result.get("forms_checked", 0)
        summary_lines.append(f"• Forms: {forms_passed}/{forms_checked} passed")
        
        # Fields
        summary_lines.append(f"• Fields: {fields_checked} checked, {len(fields_missing)} missing")
        
        # Blocking
        if blocking_issues:
            summary_lines.append("\n⚠️ BLOCKING ISSUES:")
            for issue in blocking_issues:
                summary_lines.append(f"  - {issue}")
        
        summary = "\n".join(summary_lines)
        
        logger.info("=" * 80)
        logger.info(f"DISCLOSURE VERIFICATION COMPLETE - Status: {status.upper()}")
        logger.info("=" * 80)
        
        return {
            "loan_id": loan_id,
            "status": status,
            "is_mvp_supported": is_mvp_supported,
            # v2 additions
            "trid_compliance": trid_result,
            "lock_status": lock_result,
            "form_validation": form_result,
            # G1: Hard stop result
            "hard_stop_check": hard_stop_result,
            # G8: Closing date result
            "closing_date_check": closing_date_result,
            # Original
            "fields_checked": fields_checked,
            "fields_with_values": field_result.get("fields_with_values", []),
            "fields_missing": fields_missing,
            "field_details": field_result.get("field_details", {}),
            "loan_type": field_result.get("loan_type"),
            "property_state": field_result.get("property_state"),
            "blocking_issues": blocking_issues,
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
            "fields_missing": [],
            "blocking_issues": [str(e)]
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
