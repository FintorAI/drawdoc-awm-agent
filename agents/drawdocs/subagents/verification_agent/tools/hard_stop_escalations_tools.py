"""
Hard Stop Escalations Tools.

Implements critical hard stops that require immediate escalation and halt processing.

Per SOP:
1. Approval Expiration: Note date cannot be beyond Approval expiration date
2. Random fees in Section A: Manager approval required
3. Pre-Funding QC flagged: Wait for QC clearance
4. ARM Lock Desk approval: Must be approved before docs go out

These are HARD STOPS - processing must halt and escalate to Team Lead/Manager.
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

class HardStopFields:
    """Encompass field IDs for hard stop checks."""
    
    # Approval Expiration
    APPROVAL_EXPIRATION_DATE = "2302"  # Approval Expiration Date
    NOTE_DATE = None  # Note Date - field not accessible in Encompass
    
    # Loan Type (for ARM check)
    LOAN_TYPE = "1172"  # Loan Type
    AMORTIZATION_TYPE = "LE1.X5"  # Product/Amortization Type (LE form)
    
    # Pre-Funding QC
    PRE_FUNDING_QC_FLAG = "CX.CUST01FV"  # Pre-Funding QC Status (QC Status dropdown)
    PRE_FUNDING_QC_STATUS = "CX.CUST01FV"  # Pre-Funding QC Status
    
    # ARM Lock Desk
    ARM_LOCK_DESK_APPROVED = None  # ARM Lock Desk Approved - field not available in system
    ARM_LOCK_DESK_STATUS = None  # ARM Lock Desk Status - field not available in system
    
    # Section A Fees (for random fee check)
    # Note: Section A fees are in CD form - need to check CD Section A fields
    SECTION_A_FEES = []  # List of Section A fee field IDs - need manual identification


# =============================================================================
# HARD STOP DEFINITIONS
# =============================================================================

HARD_STOP_SEVERITY = "CRITICAL"
HARD_STOP_ACTION = "HALT_PROCESSING"


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

def validate_hard_stops(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive hard stop validation.
    
    Checks for:
    1. Approval Expiration: Note date vs Approval expiration date
    2. Random fees in Section A: Unusual fees requiring manager approval
    3. Pre-Funding QC flagged: QC clearance required
    4. ARM Lock Desk approval: ARM loans must be approved by Lock Desk
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with hard stop results
    """
    logger.info(f"[HARD STOPS] Starting hard stop validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "hard_stops_found": False,
        "hard_stops": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context
        logger.info("[HARD STOPS] Reading loan context...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        loan_type = loan_context.get("loan_type", "").upper()
        result["details"].append(f"Loan Type: {loan_type}")
        
        # Read basic fields
        fields = read_fields(loan_id, [
            HardStopFields.LOAN_TYPE,
            HardStopFields.APPROVAL_EXPIRATION_DATE,
            HardStopFields.PRE_FUNDING_QC_FLAG,
        ])
        
        # =====================================================================
        # 1. APPROVAL EXPIRATION CHECK
        # =====================================================================
        logger.info("[HARD STOPS] Checking Approval Expiration...")
        approval_check = check_approval_expiration(loan_id, fields)
        if approval_check.get("is_hard_stop"):
            result["hard_stops_found"] = True
            result["hard_stops"].append({
                "type": "approval_expiration",
                "severity": HARD_STOP_SEVERITY,
                "action": HARD_STOP_ACTION,
                "title": "Approval Expiration Violation",
                "message": approval_check.get("message", ""),
                "details": approval_check.get("details", {}),
                "escalation_required": "Underwriter",
                "sop_reference": "SOP Update 26 - Check Approval Expiration dates"
            })
            logger.critical(f"[HARD STOPS] 🛑 APPROVAL EXPIRATION HARD STOP: {approval_check.get('message')}")
        elif approval_check.get("warning"):
            result["warnings"].append({
                "type": "WARNING",
                "message": approval_check.get("warning"),
                "action_required": "Verify Approval Expiration Date field ID"
            })
        
        # =====================================================================
        # 2. ARM LOCK DESK APPROVAL CHECK
        # =====================================================================
        logger.info("[HARD STOPS] Checking ARM Lock Desk approval...")
        is_arm = is_arm_loan(loan_id, fields, loan_context)
        if is_arm:
            arm_check = check_arm_lock_desk_approval(loan_id, fields)
            if arm_check.get("is_hard_stop"):
                result["hard_stops_found"] = True
                result["hard_stops"].append({
                    "type": "arm_lock_desk",
                    "severity": HARD_STOP_SEVERITY,
                    "action": HARD_STOP_ACTION,
                    "title": "ARM Lock Desk Approval Required",
                    "message": arm_check.get("message", ""),
                    "details": arm_check.get("details", {}),
                    "escalation_required": "Lock Desk Team",
                    "sop_reference": "SOP Update 12 - ARM loans must be cleared by Lock Desk Team"
                })
                logger.critical(f"[HARD STOPS] 🛑 ARM LOCK DESK HARD STOP: {arm_check.get('message')}")
            elif arm_check.get("warning"):
                result["warnings"].append({
                    "type": "WARNING",
                    "message": arm_check.get("warning"),
                    "action_required": "Verify ARM Lock Desk approval field ID"
                })
        
        # =====================================================================
        # 3. PRE-FUNDING QC FLAG CHECK
        # =====================================================================
        logger.info("[HARD STOPS] Checking Pre-Funding QC flag...")
        qc_check = check_pre_funding_qc(loan_id, fields)
        if qc_check.get("is_hard_stop"):
            result["hard_stops_found"] = True
            result["hard_stops"].append({
                "type": "pre_funding_qc",
                "severity": HARD_STOP_SEVERITY,
                "action": HARD_STOP_ACTION,
                "title": "Pre-Funding QC Flagged",
                "message": qc_check.get("message", ""),
                "details": qc_check.get("details", {}),
                "escalation_required": "QC Manager",
                "sop_reference": "SOP Update 73 - Pre-Funding QC Form"
            })
            logger.critical(f"[HARD STOPS] 🛑 PRE-FUNDING QC HARD STOP: {qc_check.get('message')}")
        elif qc_check.get("warning"):
            result["warnings"].append({
                "type": "WARNING",
                "message": qc_check.get("warning"),
                "action_required": "Verify Pre-Funding QC flag field ID"
            })
        
        # =====================================================================
        # 4. RANDOM FEES IN SECTION A CHECK
        # =====================================================================
        logger.info("[HARD STOPS] Checking for random fees in Section A...")
        random_fees_check = check_random_fees_section_a(loan_id, fields)
        if random_fees_check.get("is_hard_stop"):
            result["hard_stops_found"] = True
            result["hard_stops"].append({
                "type": "random_fees_section_a",
                "severity": HARD_STOP_SEVERITY,
                "action": HARD_STOP_ACTION,
                "title": "Random Fees in Section A - Manager Approval Required",
                "message": random_fees_check.get("message", ""),
                "details": random_fees_check.get("details", {}),
                "escalation_required": "Team Lead / Manager",
                "sop_reference": "SOP Update 35 - Random fees in Section A"
            })
            logger.critical(f"[HARD STOPS] 🛑 RANDOM FEES HARD STOP: {random_fees_check.get('message')}")
        elif random_fees_check.get("warning"):
            result["warnings"].append({
                "type": "WARNING",
                "message": random_fees_check.get("warning"),
                "action_required": "Verify Section A fee field IDs"
            })
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        if result["hard_stops_found"]:
            result["status"] = "hard_stops_found"
            logger.critical("\n" + "="*80)
            logger.critical(f"[HARD STOPS] 🛑 {len(result['hard_stops'])} HARD STOP(S) FOUND - PROCESSING MUST HALT")
            logger.critical("="*80)
            for stop in result["hard_stops"]:
                logger.critical(f"[HARD STOPS]   - {stop['title']}: {stop['message']}")
                logger.critical(f"[HARD STOPS]     Escalate to: {stop['escalation_required']}")
        else:
            result["status"] = "no_hard_stops"
            logger.info("\n" + "="*80)
            logger.info(f"[HARD STOPS] ✅ NO HARD STOPS FOUND")
            logger.info("="*80)
        
        result["details"].append(f"Hard stops found: {len(result['hard_stops'])}")
        result["details"].append(f"Warnings: {len(result['warnings'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[HARD STOPS] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# INDIVIDUAL HARD STOP CHECKS
# =============================================================================

def check_approval_expiration(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check Approval Expiration vs Note Date.
    
    Per SOP Update 26:
    - Note date on DOCS cannot be beyond Approval expiration date
    - If Approval is expiring before NOTE Date, reach out to UW to update
    
    Returns:
        Dictionary with is_hard_stop flag and message
    """
    result = {
        "is_hard_stop": False,
        "message": "",
        "details": {}
    }
    
    # Check Approval Expiration Date (Note Date still needed)
    if HardStopFields.APPROVAL_EXPIRATION_DATE:
        approval_exp_str = fields.get(HardStopFields.APPROVAL_EXPIRATION_DATE)
        
        if approval_exp_str:
            # For now, check if approval is expired (compare to today)
            # Note: Full check requires Note Date field ID
            from datetime import datetime
            try:
                approval_exp_date = datetime.strptime(str(approval_exp_str).split()[0], "%Y-%m-%d")
                today = datetime.now()
                
                # Check if Approval is expired
                if approval_exp_date < today:
                    result["is_hard_stop"] = True
                    result["message"] = f"Approval Expiration Date ({approval_exp_str}) has passed - UW must update Approval Expiration"
                    result["details"] = {
                        "approval_expiration_date": approval_exp_str,
                        "days_expired": (today - approval_exp_date).days
                    }
                # If Note Date field ID is available, check Note Date vs Approval Expiration
                if HardStopFields.NOTE_DATE:
                    note_date_str = fields.get(HardStopFields.NOTE_DATE)
                    if note_date_str:
                        try:
                            note_date = datetime.strptime(str(note_date_str).split()[0], "%Y-%m-%d")
                            
                            # Check if Note Date is beyond Approval Expiration
                            if note_date > approval_exp_date:
                                result["is_hard_stop"] = True
                                result["message"] = f"Note Date ({note_date_str}) is beyond Approval Expiration Date ({approval_exp_str})"
                                result["details"] = {
                                    "note_date": note_date_str,
                                    "approval_expiration_date": approval_exp_str,
                                    "days_over": (note_date - approval_exp_date).days
                                }
                            # Check if Approval is expiring before Note Date
                            elif approval_exp_date < note_date:
                                result["is_hard_stop"] = True
                                result["message"] = f"Approval Expiration Date ({approval_exp_str}) is before Note Date ({note_date_str}) - UW must update Approval Expiration"
                                result["details"] = {
                                    "note_date": note_date_str,
                                    "approval_expiration_date": approval_exp_str,
                                    "days_before": (note_date - approval_exp_date).days
                                }
                        except Exception as e:
                            logger.warning(f"[HARD STOPS] Error parsing Note Date: {e}")
            except Exception as e:
                logger.warning(f"[HARD STOPS] Error parsing Approval Expiration Date: {e}")
                result["warning"] = "Could not parse Approval Expiration Date"
    else:
        result["warning"] = "Approval Expiration Date or Note Date field ID not found - manual verification required"
    
    return result


def is_arm_loan(loan_id: str, fields: Dict[str, Any], loan_context: Dict[str, Any]) -> bool:
    """
    Check if loan is an ARM (Adjustable Rate Mortgage).
    
    Returns:
        True if ARM loan, False otherwise
    """
    # Check amortization type
    if HardStopFields.AMORTIZATION_TYPE:
        amortization = fields.get(HardStopFields.AMORTIZATION_TYPE, "").upper()
        if "ARM" in amortization or "ADJUSTABLE" in amortization:
            return True
    
    # Check loan type description
    loan_type = loan_context.get("loan_type", "").upper()
    if "ARM" in loan_type or "ADJUSTABLE" in loan_type:
        return True
    
    # Check loan program
    loan_program = loan_context.get("loan_program", "").upper()
    if "ARM" in loan_program:
        return True
    
    return False


def check_arm_lock_desk_approval(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check ARM Lock Desk approval.
    
    Per SOP Update 12:
    - ARM loans must be cleared/reviewed by Lock Desk Team before docs go out
    - NO EXCEPTIONS
    - Do not send DOCS Out until they say ok
    
    Returns:
        Dictionary with is_hard_stop flag and message
    """
    result = {
        "is_hard_stop": False,
        "message": "",
        "details": {}
    }
    
    # TODO: Need ARM Lock Desk approval field ID
    if HardStopFields.ARM_LOCK_DESK_APPROVED:
        lock_desk_approved = fields.get(HardStopFields.ARM_LOCK_DESK_APPROVED)
        
        if lock_desk_approved is None:
            result["is_hard_stop"] = True
            result["message"] = "ARM loan - Lock Desk approval status unknown or not set"
            result["details"] = {"lock_desk_approved": None}
        elif not lock_desk_approved or str(lock_desk_approved).upper() not in ["YES", "TRUE", "APPROVED", "OK"]:
            result["is_hard_stop"] = True
            result["message"] = f"ARM loan - Lock Desk approval not received (Status: {lock_desk_approved})"
            result["details"] = {"lock_desk_approved": lock_desk_approved}
    else:
        result["warning"] = "ARM Lock Desk approval field ID not found - manual verification required for ARM loans"
    
    return result


def check_pre_funding_qc(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check Pre-Funding QC flag.
    
    Per SOP Update 73:
    - Pre-Funding QC flagged loans must wait for QC clearance
    - HARDSTOP - do not proceed until cleared
    
    Returns:
        Dictionary with is_hard_stop flag and message
    """
    result = {
        "is_hard_stop": False,
        "message": "",
        "details": {}
    }
    
    # Check Pre-Funding QC flag
    if HardStopFields.PRE_FUNDING_QC_FLAG:
        qc_status = fields.get(HardStopFields.PRE_FUNDING_QC_FLAG, "")
        
        # Check if QC status indicates a flag (not "Complete" or "Pass")
        if qc_status and str(qc_status).upper() not in ["COMPLETE", "PASS", "PASSED", "OK"]:
            result["is_hard_stop"] = True
            result["message"] = f"Pre-Funding QC flagged - Status: {qc_status}"
            result["details"] = {
                "qc_status": qc_status
            }
    else:
        result["warning"] = "Pre-Funding QC flag field ID not found - manual verification required"
    
    return result


def check_random_fees_section_a(loan_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check for random/unusual fees in Section A.
    
    Per SOP Update 35:
    - Random fees in Section A (e.g., ADMIN, ADMINISTRATION FEE) require manager approval
    - File won't leave queue without lead's approval
    - Must be brought to Team Lead/Manager notice
    
    Returns:
        Dictionary with is_hard_stop flag and message
    """
    result = {
        "is_hard_stop": False,
        "message": "",
        "details": {}
    }
    
    # List of known random/unusual fees that require approval
    RANDOM_FEE_KEYWORDS = [
        "ADMIN", "ADMINISTRATION", "ADMINISTRATIVE",
        "PROCESSING", "UNDERWRITING", "ORIGINATION",
        "APPLICATION", "COMMITMENT", "DOCUMENT PREPARATION",
        "WIRE TRANSFER", "COURIER", "EXPRESS"
    ]
    
    # TODO: Need Section A fee field IDs
    # Section A fees are typically in CD form fields
    # For now, we'll flag this as needing manual verification
    
    if HardStopFields.SECTION_A_FEES:
        random_fees_found = []
        
        for fee_field_id in HardStopFields.SECTION_A_FEES:
            fee_name = fields.get(fee_field_id)
            fee_amount = fields.get(f"{fee_field_id}_AMOUNT")
            
            if fee_name:
                fee_name_upper = str(fee_name).upper()
                for keyword in RANDOM_FEE_KEYWORDS:
                    if keyword in fee_name_upper:
                        random_fees_found.append({
                            "fee_name": fee_name,
                            "fee_amount": fee_amount,
                            "field_id": fee_field_id
                        })
                        break
        
        if random_fees_found:
            result["is_hard_stop"] = True
            result["message"] = f"Random/unusual fees found in Section A: {', '.join([f['fee_name'] for f in random_fees_found])}"
            result["details"] = {
                "random_fees": random_fees_found,
                "count": len(random_fees_found)
            }
    else:
        result["warning"] = "Section A fee field IDs not found - manual verification required for random fees"
    
    return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "validate_hard_stops",
    "check_approval_expiration",
    "is_arm_loan",
    "check_arm_lock_desk_approval",
    "check_pre_funding_qc",
    "check_random_fees_section_a",
]

