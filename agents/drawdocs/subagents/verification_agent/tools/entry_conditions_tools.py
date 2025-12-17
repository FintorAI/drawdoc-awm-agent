"""
Entry Conditions (Prerequisites) Validation Tools.

Validates that a loan meets ALL prerequisites before DrawDocs processing can begin.

Per SOP Entry Conditions:
- CTC Status: Must be "Clear to Close" (bold)
- CD Approved: CD Status must say "CD Approved"
- CD Acknowledged: Initial CD must be signed/acknowledged by Borrower(s)
- 3-Day Waiting Period: TRID CFPB 3-day waiting period must have passed
- Docs Ordered Queue: File must be in "Closer – Docs Ordered" pipeline

These are HARD STOPS - loan cannot proceed if any fail.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, get_loan_context

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS
# =============================================================================

class EntryConditionFields:
    """Encompass field IDs for entry condition validation."""
    
    # Milestone fields
    CTC_STATUS = "Log.MS.Status.Clear to Close"  # CTC milestone status
    CTC_DATE = "Log.MS.Date.Clear to Close"  # CTC milestone date
    CURRENT_MILESTONE = "Log.MS.CurrentMilestone"  # Current milestone name
    
    # CD Approval fields (from primitives.py)
    CD_LO_APPROVAL = "CX.CD.REQ.APPROVAL.LO"  # LO approval flag
    CD_PROC_APPROVAL = "CX.CD.REQ.APPROVAL.PROC"  # Processor confirmation flag
    
    # CD Acknowledgment fields
    CD_ACKNOWLEDGED = "CD1.X90"  # CD Acknowledged checkbox/field
    CD_ACK_DATE = "CD1.X51"  # Disclosure Received Date (CD acknowledgment date)
    
    # Closing Date
    CLOSING_DATE = "748"  # Estimated Closing Date


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_date(date_str: Any) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str or date_str == "":
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        # Try common date formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def is_business_day(date: datetime) -> bool:
    """Check if date is a business day (Monday-Friday)."""
    return date.weekday() < 5  # 0-4 = Monday-Friday


def add_business_days(start_date: datetime, days: int) -> datetime:
    """Add business days to a date."""
    current_date = start_date
    days_added = 0
    
    while days_added < days:
        current_date += timedelta(days=1)
        if is_business_day(current_date):
            days_added += 1
    
    return current_date


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_entry_conditions(loan_id: str) -> Dict[str, Any]:
    """
    Validate ALL entry conditions (prerequisites) before DrawDocs processing.
    
    Per SOP Entry Conditions:
    1. CTC Status: Must be "Clear to Close" (bold)
    2. CD Approved: CD Status must say "CD Approved"
    3. CD Acknowledged: Initial CD must be signed/acknowledged by Borrower(s)
    4. 3-Day Waiting Period: TRID CFPB 3-day waiting period must have passed
    5. Docs Ordered Queue: File must be in "Closer – Docs Ordered" pipeline
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results and blocking conditions
    """
    import os
    
    logger.info(f"[ENTRY CONDITIONS] Starting validation for loan {loan_id}")
    
    # Check if we're in demo mode
    is_demo_mode = os.getenv("ENABLE_ENCOMPASS_WRITES", "true").lower() == "false"
    
    if is_demo_mode:
        logger.info("[ENTRY CONDITIONS] 🔍 DEMO MODE - Auto-passing all prerequisites")
        return {
            "status": "passed_demo_mode",
            "loan_id": loan_id,
            "all_conditions_met": True,
            "blocking_conditions": [],
            "warnings": ["Demo mode active - prerequisites not validated"],
            "conditions": {
                "ctc_status": {"passed": True, "message": "Demo mode - skipped"},
                "cd_approved": {"passed": True, "message": "Demo mode - skipped"},
                "cd_acknowledged": {"passed": True, "message": "Demo mode - skipped"},
                "three_day_waiting": {"passed": True, "message": "Demo mode - skipped"},
                "docs_ordered_queue": {"passed": True, "message": "Demo mode - skipped"}
            },
            "details": ["Demo mode active - all prerequisites automatically passed for testing"]
        }
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "all_conditions_met": False,
        "blocking_conditions": [],
        "warnings": [],
        "conditions": {
            "ctc_status": None,
            "cd_approved": None,
            "cd_acknowledged": None,
            "three_day_waiting": None,
            "docs_ordered_queue": None
        },
        "details": []
    }
    
    try:
        # Get loan context for milestone and pipeline info
        logger.info("[ENTRY CONDITIONS] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=True)
        
        # Read CD-related fields
        logger.info("[ENTRY CONDITIONS] Reading CD approval and acknowledgment fields...")
        fields = read_fields(loan_id, [
            EntryConditionFields.CTC_STATUS,
            EntryConditionFields.CTC_DATE,
            EntryConditionFields.CURRENT_MILESTONE,
            EntryConditionFields.CD_LO_APPROVAL,
            EntryConditionFields.CD_PROC_APPROVAL,
            EntryConditionFields.CD_ACKNOWLEDGED,
            EntryConditionFields.CD_ACK_DATE,
            EntryConditionFields.CLOSING_DATE,
        ])
        
        # =====================================================================
        # CONDITION 1: CTC STATUS
        # =====================================================================
        logger.info("\n[ENTRY CONDITIONS] Checking CTC Status...")
        ctc_result = validate_ctc_status(loan_context)
        result["conditions"]["ctc_status"] = ctc_result
        
        if not ctc_result["passed"]:
            result["blocking_conditions"].append({
                "condition": "CTC Status",
                "severity": "HARD_STOP",
                "message": ctc_result["message"],
                "details": ctc_result.get("details", {}),
                "action_required": "Loan must be in 'Clear to Close' milestone status before DrawDocs processing"
            })
            logger.error(f"[ENTRY CONDITIONS] ❌ CTC Status: {ctc_result['message']}")
        else:
            logger.info(f"[ENTRY CONDITIONS] ✅ CTC Status: {ctc_result['message']}")
        
        # =====================================================================
        # CONDITION 2: CD APPROVED
        # =====================================================================
        logger.info("\n[ENTRY CONDITIONS] Checking CD Approved Status...")
        cd_approved_result = validate_cd_approved(fields, loan_context)
        result["conditions"]["cd_approved"] = cd_approved_result
        
        if not cd_approved_result["passed"]:
            result["blocking_conditions"].append({
                "condition": "CD Approved",
                "severity": "HARD_STOP",
                "message": cd_approved_result["message"],
                "details": cd_approved_result.get("details", {}),
                "action_required": "CD Status must be 'CD Approved' before DrawDocs processing"
            })
            logger.error(f"[ENTRY CONDITIONS] ❌ CD Approved: {cd_approved_result['message']}")
        else:
            logger.info(f"[ENTRY CONDITIONS] ✅ CD Approved: {cd_approved_result['message']}")
        
        # =====================================================================
        # CONDITION 3: CD ACKNOWLEDGED
        # =====================================================================
        logger.info("\n[ENTRY CONDITIONS] Checking CD Acknowledged...")
        cd_ack_result = validate_cd_acknowledged(fields)
        result["conditions"]["cd_acknowledged"] = cd_ack_result
        
        if not cd_ack_result["passed"]:
            result["blocking_conditions"].append({
                "condition": "CD Acknowledged",
                "severity": "HARD_STOP",
                "message": cd_ack_result["message"],
                "details": cd_ack_result.get("details", {}),
                "action_required": "Initial CD must be signed/acknowledged by Borrower(s) before DrawDocs processing"
            })
            logger.error(f"[ENTRY CONDITIONS] ❌ CD Acknowledged: {cd_ack_result['message']}")
        else:
            logger.info(f"[ENTRY CONDITIONS] ✅ CD Acknowledged: {cd_ack_result['message']}")
        
        # =====================================================================
        # CONDITION 4: 3-DAY WAITING PERIOD
        # =====================================================================
        logger.info("\n[ENTRY CONDITIONS] Checking 3-Day Waiting Period...")
        waiting_period_result = validate_three_day_waiting_period(fields)
        result["conditions"]["three_day_waiting"] = waiting_period_result
        
        if not waiting_period_result["passed"]:
            result["blocking_conditions"].append({
                "condition": "3-Day Waiting Period",
                "severity": "HARD_STOP",
                "message": waiting_period_result["message"],
                "details": waiting_period_result.get("details", {}),
                "action_required": "TRID CFPB 3-day waiting period must have passed before DrawDocs processing"
            })
            logger.error(f"[ENTRY CONDITIONS] ❌ 3-Day Waiting: {waiting_period_result['message']}")
        else:
            logger.info(f"[ENTRY CONDITIONS] ✅ 3-Day Waiting: {waiting_period_result['message']}")
        
        # =====================================================================
        # CONDITION 5: DOCS ORDERED QUEUE
        # =====================================================================
        logger.info("\n[ENTRY CONDITIONS] Checking Docs Ordered Queue...")
        queue_result = validate_docs_ordered_queue(loan_context)
        result["conditions"]["docs_ordered_queue"] = queue_result
        
        if not queue_result["passed"]:
            result["blocking_conditions"].append({
                "condition": "Docs Ordered Queue",
                "severity": "HARD_STOP",
                "message": queue_result["message"],
                "details": queue_result.get("details", {}),
                "action_required": "Loan must be in 'Closer – Docs Ordered' pipeline before DrawDocs processing"
            })
            logger.error(f"[ENTRY CONDITIONS] ❌ Docs Ordered Queue: {queue_result['message']}")
        else:
            logger.info(f"[ENTRY CONDITIONS] ✅ Docs Ordered Queue: {queue_result['message']}")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        all_passed = all([
            ctc_result["passed"],
            cd_approved_result["passed"],
            cd_ack_result["passed"],
            waiting_period_result["passed"],
            queue_result["passed"]
        ])
        
        result["all_conditions_met"] = all_passed
        
        if all_passed:
            result["status"] = "all_conditions_met"
            logger.info("\n" + "="*80)
            logger.info("[ENTRY CONDITIONS] ✅ ALL ENTRY CONDITIONS MET - Loan ready for DrawDocs processing")
            logger.info("="*80)
        else:
            result["status"] = "blocking_conditions_found"
            logger.warning("\n" + "="*80)
            logger.warning(f"[ENTRY CONDITIONS] ❌ BLOCKING CONDITIONS FOUND: {len(result['blocking_conditions'])} conditions not met")
            logger.warning("="*80)
            for block in result["blocking_conditions"]:
                logger.warning(f"  - {block['condition']}: {block['message']}")
        
        # Add summary details
        result["details"].append(f"CTC Status: {'✅ Pass' if ctc_result['passed'] else '❌ Fail'}")
        result["details"].append(f"CD Approved: {'✅ Pass' if cd_approved_result['passed'] else '❌ Fail'}")
        result["details"].append(f"CD Acknowledged: {'✅ Pass' if cd_ack_result['passed'] else '❌ Fail'}")
        result["details"].append(f"3-Day Waiting: {'✅ Pass' if waiting_period_result['passed'] else '❌ Fail'}")
        result["details"].append(f"Docs Ordered Queue: {'✅ Pass' if queue_result['passed'] else '❌ Fail'}")
        
        return result
        
    except Exception as e:
        logger.error(f"[ENTRY CONDITIONS] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# INDIVIDUAL CONDITION VALIDATORS
# =============================================================================

def validate_ctc_status(loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate CTC (Clear to Close) status.
    
    Per SOP: Milestone must be "Clear to Close" (bold).
    
    Args:
        loan_context: Loan context from get_loan_context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    # Check flags first (from get_loan_context)
    flags = loan_context.get("flags", {})
    is_ctc = flags.get("is_ctc", False)
    
    # Also check milestones if available
    milestones = loan_context.get("milestones", {})
    clear_to_close = milestones.get("clear_to_close")
    
    result["details"]["is_ctc_flag"] = is_ctc
    result["details"]["clear_to_close_milestone"] = clear_to_close
    
    if clear_to_close:
        milestone_name = clear_to_close.get("name", "")
        milestone_status = clear_to_close.get("status", "")
        result["details"]["milestone_name"] = milestone_name
        result["details"]["milestone_status"] = milestone_status
        
        # Check if milestone is "Clear to Close" and status is "Finished"
        if "clear to close" in str(milestone_name).lower():
            if milestone_status and "finished" in str(milestone_status).lower():
                result["passed"] = True
                result["message"] = f"CTC milestone active: {milestone_name} (Status: {milestone_status})"
            else:
                result["passed"] = False
                result["message"] = f"CTC milestone found but status is '{milestone_status}' (expected 'Finished')"
        else:
            result["passed"] = False
            result["message"] = f"Current milestone is '{milestone_name}' (expected 'Clear to Close')"
    elif is_ctc:
        # Fallback to flag if milestone data not available
        result["passed"] = True
        result["message"] = "CTC status confirmed via flags"
    else:
        result["passed"] = False
        result["message"] = "CTC milestone not found or not active"
    
    return result


def validate_cd_approved(fields: Dict[str, Any], loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate CD Approved status.
    
    Per SOP: CD Status must say "CD Approved".
    Checks: CX.CD.REQ.APPROVAL.LO (LO approval) and CX.CD.REQ.APPROVAL.PROC (Processor confirmation).
    
    Args:
        fields: Field values from read_fields
        loan_context: Loan context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    # Check flags first (from get_loan_context)
    flags = loan_context.get("flags", {})
    cd_approved_flag = flags.get("cd_approved", False)
    
    # Also check fields directly
    lo_approval = fields.get(EntryConditionFields.CD_LO_APPROVAL, "")
    proc_approval = fields.get(EntryConditionFields.CD_PROC_APPROVAL, "")
    
    # Check if LO approved - could be "Y", "Yes", "true", True, "1", etc.
    lo_approved = str(lo_approval).lower() in ["y", "yes", "true", "1", "x"] if lo_approval else False
    proc_approved = str(proc_approval).lower() in ["y", "yes", "true", "1", "x"] if proc_approval else False
    
    result["details"]["cd_approved_flag"] = cd_approved_flag
    result["details"]["lo_approval"] = lo_approval
    result["details"]["proc_approval"] = proc_approval
    result["details"]["lo_approved"] = lo_approved
    result["details"]["proc_approved"] = proc_approved
    
    if cd_approved_flag:
        result["passed"] = True
        result["message"] = "CD Approved status confirmed via flags"
    elif lo_approved:
        result["passed"] = True
        result["message"] = f"CD Approved by LO (LO Approval: {lo_approval}, Processor: {proc_approval})"
    else:
        result["passed"] = False
        result["message"] = f"CD NOT APPROVED - LO Approval: {lo_approval or 'Empty'}, Processor: {proc_approval or 'Empty'}"
    
    return result


def validate_cd_acknowledged(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate CD Acknowledged by Borrower(s).
    
    Per SOP: Initial CD must be signed/acknowledged by Borrower(s).
    
    Args:
        fields: Field values from read_fields
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    cd_acknowledged = fields.get(EntryConditionFields.CD_ACKNOWLEDGED)
    cd_ack_date = fields.get(EntryConditionFields.CD_ACK_DATE)
    
    result["details"]["cd_acknowledged"] = cd_acknowledged
    result["details"]["cd_ack_date"] = cd_ack_date
    
    # Check if CD is acknowledged
    # CD acknowledged can be a checkbox (X, Y, 1, true) or a date field
    is_acknowledged = False
    
    if cd_acknowledged:
        ack_str = str(cd_acknowledged).strip().upper()
        if ack_str in ["X", "Y", "1", "TRUE", "YES"]:
            is_acknowledged = True
        elif cd_ack_date:  # If date exists, consider it acknowledged
            is_acknowledged = True
    
    if is_acknowledged:
        result["passed"] = True
        result["message"] = f"CD Acknowledged (Date: {cd_ack_date})"
    else:
        result["passed"] = False
        result["message"] = "CD not acknowledged by Borrower(s)"
    
    return result


def validate_three_day_waiting_period(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate 3-Day Waiting Period.
    
    Per SOP: TRID CFPB 3-day waiting period must have passed.
    Calculate: CD ACK date + 3 business days must be <= today.
    
    Args:
        fields: Field values from read_fields
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    cd_ack_date = fields.get(EntryConditionFields.CD_ACK_DATE)
    closing_date = fields.get(EntryConditionFields.CLOSING_DATE)
    
    result["details"]["cd_ack_date"] = cd_ack_date
    result["details"]["closing_date"] = closing_date
    
    if not cd_ack_date:
        result["passed"] = False
        result["message"] = "CD Acknowledgment date not found - cannot calculate 3-day waiting period"
        return result
    
    # Parse CD acknowledgment date
    ack_date = parse_date(cd_ack_date)
    if not ack_date:
        result["passed"] = False
        result["message"] = f"CD Acknowledgment date '{cd_ack_date}' could not be parsed"
        return result
    
    # Calculate 3 business days after acknowledgment
    three_business_days_later = add_business_days(ack_date, 3)
    today = datetime.now().date()
    
    result["details"]["ack_date"] = ack_date.date().isoformat()
    result["details"]["three_business_days_later"] = three_business_days_later.date().isoformat()
    result["details"]["today"] = today.isoformat()
    
    # Check if 3 business days have passed
    if three_business_days_later.date() <= today:
        result["passed"] = True
        result["message"] = f"3-day waiting period passed (ACK: {ack_date.date()}, 3 days later: {three_business_days_later.date()})"
    else:
        days_remaining = (three_business_days_later.date() - today).days
        result["passed"] = False
        result["message"] = f"3-day waiting period not yet passed ({days_remaining} business days remaining)"
    
    return result


def validate_docs_ordered_queue(loan_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Docs Ordered Queue.
    
    Per SOP: File must be in "Closer – Docs Ordered" pipeline.
    
    Args:
        loan_context: Loan context from get_loan_context
        
    Returns:
        Dictionary with validation result
    """
    result = {
        "passed": False,
        "message": "",
        "details": {}
    }
    
    # Check flags first (from get_loan_context)
    flags = loan_context.get("flags", {})
    in_docs_ordered_queue = flags.get("in_docs_ordered_queue", False)
    
    # Also check milestones if available
    milestones = loan_context.get("milestones", {})
    docs_ordered = milestones.get("docs_ordered")
    
    result["details"]["in_docs_ordered_queue_flag"] = in_docs_ordered_queue
    result["details"]["docs_ordered_milestone"] = docs_ordered
    
    if in_docs_ordered_queue:
        result["passed"] = True
        result["message"] = "Loan in Docs Ordered pipeline (confirmed via flags)"
    elif docs_ordered:
        milestone_name = docs_ordered.get("name", "")
        milestone_status = docs_ordered.get("status", "")
        result["details"]["milestone_name"] = milestone_name
        result["details"]["milestone_status"] = milestone_status
        
        if "docs ordered" in str(milestone_name).lower():
            if milestone_status in ["Started", "InProgress"]:
                result["passed"] = True
                result["message"] = f"Loan in Docs Ordered milestone: {milestone_name} (Status: {milestone_status})"
            else:
                result["passed"] = False
                result["message"] = f"Docs Ordered milestone found but status is '{milestone_status}' (expected 'Started' or 'InProgress')"
        else:
            result["passed"] = False
            result["message"] = f"Current milestone is '{milestone_name}' (expected 'Docs Ordered')"
    else:
        result["passed"] = False
        result["message"] = "Loan not in Docs Ordered pipeline or milestone"
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_entry_conditions",
    "validate_ctc_status",
    "validate_cd_approved",
    "validate_cd_acknowledged",
    "validate_three_day_waiting_period",
    "validate_docs_ordered_queue",
]

