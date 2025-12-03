"""Milestone, Disclosure Tracking, and Pre-Check for Disclosure Agent.

Per SOP: 
- Check disclosure tracking - ensure disclosure NOT sent yet
- Check "Send Initial Disclosures" alert is present
- Verify loan status is eligible for disclosure
"""

import os
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import date, datetime
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .auth import get_access_token
from .encompass_io import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD IDs FOR MILESTONE/STATUS
# =============================================================================

LOAN_STATUS_FIELD = "1393"  # Current Status of File
MILESTONE_FIELD = "1987"  # Current Milestone  
APPLICATION_DATE_FIELD = "745"  # Application Date


# =============================================================================
# EXPECTED VALUES
# =============================================================================

VALID_STATUSES_FOR_DISCLOSURE = [
    "Active",
    "Application",
    "Processing",
    "Submitted",
    "Loan Submitted",
]

BLOCKING_STATUSES = [
    "Loan Originated",
    "Funded", 
    "Closed",
    "Denied",
    "Withdrawn",
    "Suspended",
    "Cancelled",
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MilestoneCheckResult:
    """Result of milestone/queue pre-check."""
    can_proceed: bool
    current_status: str
    current_milestone: Optional[str] = None
    application_date: Optional[str] = None
    blocking_reason: Optional[str] = None
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_proceed": self.can_proceed,
            "current_status": self.current_status,
            "current_milestone": self.current_milestone,
            "application_date": self.application_date,
            "blocking_reason": self.blocking_reason,
            "warnings": self.warnings,
        }


@dataclass
class DisclosureTrackingResult:
    """Result of disclosure tracking check."""
    success: bool
    le_already_sent: bool = False
    cd_already_sent: bool = False
    total_disclosures: int = 0
    disclosure_logs: List[Dict] = field(default_factory=list)
    eligible_for_initial_le: bool = True
    blocking_reason: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "le_already_sent": self.le_already_sent,
            "cd_already_sent": self.cd_already_sent,
            "total_disclosures": self.total_disclosures,
            "eligible_for_initial_le": self.eligible_for_initial_le,
            "blocking_reason": self.blocking_reason,
            "error": self.error,
        }


@dataclass
class MilestoneAPIResult:
    """Result of milestones API call."""
    success: bool
    milestones: List[Dict] = field(default_factory=list)
    current_milestone: Optional[str] = None
    next_milestone: Optional[str] = None
    completed_milestones: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "current_milestone": self.current_milestone,
            "next_milestone": self.next_milestone,
            "completed_milestones": self.completed_milestones,
            "total_milestones": len(self.milestones),
            "error": self.error,
        }


@dataclass
class PreCheckResult:
    """Comprehensive pre-check result."""
    can_proceed: bool
    milestone_check: MilestoneCheckResult
    disclosure_tracking: DisclosureTrackingResult
    milestones_api: MilestoneAPIResult
    blocking_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_proceed": self.can_proceed,
            "milestone_check": self.milestone_check.to_dict() if self.milestone_check else None,
            "disclosure_tracking": self.disclosure_tracking.to_dict() if self.disclosure_tracking else None,
            "milestones_api": self.milestones_api.to_dict() if self.milestones_api else None,
            "blocking_reasons": self.blocking_reasons,
            "warnings": self.warnings,
        }


# =============================================================================
# DISCLOSURE TRACKING API
# =============================================================================

def get_disclosure_tracking_logs(loan_id: str) -> DisclosureTrackingResult:
    """Get disclosure tracking logs for a loan.
    
    Uses GET /encompass/v3/loans/{loanId}/disclosureTracking2015Logs
    
    This tells us:
    - If Initial LE has already been sent (contents contains "LE")
    - If this is a COC/Revised LE scenario
    - eConsent status, Intent to Proceed, etc.
    
    Args:
        loan_id: Loan GUID
        
    Returns:
        DisclosureTrackingResult with disclosure status
    """
    logger.info(f"[DISCLOSURE] Checking disclosure tracking for loan {loan_id[:8]}...")
    
    try:
        token = get_access_token()
        if not token:
            logger.error("[DISCLOSURE] Failed to get access token")
            return DisclosureTrackingResult(
                success=False,
                error="Failed to get access token"
            )
    except Exception as e:
        logger.error(f"[DISCLOSURE] Auth error: {e}")
        return DisclosureTrackingResult(
            success=False,
            error=f"Auth error: {str(e)}"
        )
    
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    url = f"{api_server}/encompass/v3/loans/{loan_id}/disclosureTracking2015Logs"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            logs = response.json()
            
            le_sent = False
            cd_sent = False
            
            for log in logs:
                contents = log.get("contents", [])
                if "LE" in contents:
                    le_sent = True
                if "CD" in contents:
                    cd_sent = True
            
            # Determine eligibility
            eligible_for_initial_le = not le_sent
            blocking_reason = None
            
            if le_sent:
                blocking_reason = "Initial LE already sent - this would be COC/Revised LE (not MVP)"
            
            logger.info(f"[DISCLOSURE] LE sent: {le_sent}, CD sent: {cd_sent}")
            logger.info(f"[DISCLOSURE] Eligible for Initial LE: {eligible_for_initial_le}")
            
            return DisclosureTrackingResult(
                success=True,
                le_already_sent=le_sent,
                cd_already_sent=cd_sent,
                total_disclosures=len(logs),
                disclosure_logs=logs,
                eligible_for_initial_le=eligible_for_initial_le,
                blocking_reason=blocking_reason,
            )
        else:
            logger.error(f"[DISCLOSURE] API error: {response.status_code}")
            return DisclosureTrackingResult(
                success=False,
                error=f"API error: {response.status_code} - {response.text[:100]}"
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[DISCLOSURE] Request error: {e}")
        return DisclosureTrackingResult(
            success=False,
            error=f"Request error: {str(e)}"
        )


# =============================================================================
# MILESTONES API
# =============================================================================

def get_loan_milestones(loan_id: str) -> MilestoneAPIResult:
    """Get all milestones for a loan.
    
    Uses GET /encompass/v3/loans/{loanId}/milestones
    
    Args:
        loan_id: Loan GUID
        
    Returns:
        MilestoneAPIResult with milestone status
    """
    logger.info(f"[MILESTONE] Fetching milestones for loan {loan_id[:8]}...")
    
    try:
        token = get_access_token()
        if not token:
            logger.error("[MILESTONE] Failed to get access token")
            return MilestoneAPIResult(
                success=False,
                error="Failed to get access token"
            )
    except Exception as e:
        logger.error(f"[MILESTONE] Auth error: {e}")
        return MilestoneAPIResult(
            success=False,
            error=f"Auth error: {str(e)}"
        )
    
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    url = f"{api_server}/encompass/v3/loans/{loan_id}/milestones"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            milestones = response.json()
            
            completed = []
            current = None
            next_ms = None
            
            for ms in milestones:
                name = ms.get("name", "Unknown")
                if ms.get("doneIndicator"):
                    completed.append(name)
                    current = name  # Last completed is current
                elif next_ms is None:
                    next_ms = name  # First incomplete is next
            
            logger.info(f"[MILESTONE] Current: {current}, Next: {next_ms}")
            logger.info(f"[MILESTONE] Completed: {completed}")
            
            return MilestoneAPIResult(
                success=True,
                milestones=milestones,
                current_milestone=current,
                next_milestone=next_ms,
                completed_milestones=completed,
            )
        else:
            logger.error(f"[MILESTONE] API error: {response.status_code}")
            return MilestoneAPIResult(
                success=False,
                error=f"API error: {response.status_code} - {response.text[:100]}"
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[MILESTONE] Request error: {e}")
        return MilestoneAPIResult(
            success=False,
            error=f"Request error: {str(e)}"
        )


# =============================================================================
# MILESTONE CHECKER CLASS
# =============================================================================

class MilestoneChecker:
    """Check if loan is in correct queue/milestone for disclosure processing."""
    
    def check(self, loan_id: str) -> MilestoneCheckResult:
        """Check if loan is ready for disclosure processing.
        
        Per SOP:
        1. Loan should be in "DD Request" queue
        2. Current Status should be "Active" or equivalent
        3. Application Date must be set
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            MilestoneCheckResult with can_proceed flag
        """
        logger.info(f"[MILESTONE] Checking loan {loan_id[:8]}...")
        
        try:
            fields = read_fields(loan_id, [
                LOAN_STATUS_FIELD,
                MILESTONE_FIELD,
                APPLICATION_DATE_FIELD,
            ])
            
            current_status = fields.get(LOAN_STATUS_FIELD, "Unknown")
            current_milestone = fields.get(MILESTONE_FIELD)
            application_date = fields.get(APPLICATION_DATE_FIELD)
            
            logger.info(f"[MILESTONE] Status: {current_status}")
            logger.info(f"[MILESTONE] Milestone: {current_milestone}")
            logger.info(f"[MILESTONE] App Date: {application_date}")
            
            warnings = []
            
            # Check 1: Application Date must be set
            if not application_date or application_date in ["//", ""]:
                return MilestoneCheckResult(
                    can_proceed=False,
                    current_status=current_status,
                    current_milestone=current_milestone,
                    application_date=None,
                    blocking_reason="Application Date not set - BLOCKING",
                )
            
            # Check 2: Loan Status should not be in blocking state
            if current_status in BLOCKING_STATUSES:
                return MilestoneCheckResult(
                    can_proceed=False,
                    current_status=current_status,
                    current_milestone=current_milestone,
                    application_date=application_date,
                    blocking_reason=f"Loan status '{current_status}' is not eligible for disclosure",
                )
            
            # Check 3: Warn if status is unexpected
            if current_status not in VALID_STATUSES_FOR_DISCLOSURE:
                warnings.append(f"Status '{current_status}' is unusual for disclosure processing")
            
            return MilestoneCheckResult(
                can_proceed=True,
                current_status=current_status,
                current_milestone=current_milestone,
                application_date=application_date,
                warnings=warnings,
            )
            
        except Exception as e:
            logger.error(f"[MILESTONE] Error checking milestone: {e}")
            return MilestoneCheckResult(
                can_proceed=False,
                current_status="Error",
                blocking_reason=f"Failed to read loan status: {str(e)}",
            )


# =============================================================================
# COMPREHENSIVE PRE-CHECK
# =============================================================================

def run_pre_check(loan_id: str) -> PreCheckResult:
    """Run comprehensive pre-check before disclosure processing.
    
    This runs:
    1. Milestone/status check (field-based)
    2. Disclosure tracking check (API-based)
    3. Milestones API check
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        PreCheckResult with combined results
    """
    logger.info("=" * 80)
    logger.info(f"RUNNING PRE-CHECK FOR LOAN {loan_id[:8]}")
    logger.info("=" * 80)
    
    blocking_reasons = []
    warnings = []
    
    # 1. Milestone/Status Check
    logger.info("[1/3] Checking loan status...")
    checker = MilestoneChecker()
    milestone_result = checker.check(loan_id)
    
    if not milestone_result.can_proceed:
        blocking_reasons.append(milestone_result.blocking_reason)
    if milestone_result.warnings:
        warnings.extend(milestone_result.warnings)
    
    # 2. Disclosure Tracking Check
    logger.info("[2/3] Checking disclosure tracking...")
    disclosure_result = get_disclosure_tracking_logs(loan_id)
    
    if disclosure_result.success:
        if not disclosure_result.eligible_for_initial_le:
            blocking_reasons.append(disclosure_result.blocking_reason or "Initial LE already sent")
    else:
        warnings.append(f"Could not check disclosure tracking: {disclosure_result.error}")
    
    # 3. Milestones API Check
    logger.info("[3/3] Fetching milestones...")
    milestones_result = get_loan_milestones(loan_id)
    
    if milestones_result.success:
        # Check for blocking milestones (Funding, Completion, etc.)
        blocking_milestones = ["Funding", "Post Closing", "Shipping", "Completion"]
        for ms in milestones_result.completed_milestones:
            if ms in blocking_milestones:
                blocking_reasons.append(f"Milestone '{ms}' completed - loan may be funded")
                break
    else:
        warnings.append(f"Could not fetch milestones: {milestones_result.error}")
    
    # Determine if can proceed
    can_proceed = len(blocking_reasons) == 0
    
    logger.info("=" * 80)
    logger.info(f"PRE-CHECK COMPLETE - Can proceed: {can_proceed}")
    if blocking_reasons:
        logger.warning(f"Blocking reasons: {blocking_reasons}")
    if warnings:
        logger.info(f"Warnings: {warnings}")
    logger.info("=" * 80)
    
    return PreCheckResult(
        can_proceed=can_proceed,
        milestone_check=milestone_result,
        disclosure_tracking=disclosure_result,
        milestones_api=milestones_result,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def check_milestone(loan_id: str) -> MilestoneCheckResult:
    """Check if loan is ready for disclosure processing (field-based).
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        MilestoneCheckResult with can_proceed flag
    """
    checker = MilestoneChecker()
    return checker.check(loan_id)


def is_ready_for_disclosure(loan_id: str) -> bool:
    """Quick check if loan is ready for disclosure.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        True if loan can proceed with disclosure
    """
    result = run_pre_check(loan_id)
    return result.can_proceed


def check_initial_le_eligibility(loan_id: str) -> Dict[str, Any]:
    """Check if loan is eligible for Initial LE disclosure.
    
    Runs full pre-check and returns result as dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with eligibility status and details
    """
    result = run_pre_check(loan_id)
    return result.to_dict()
