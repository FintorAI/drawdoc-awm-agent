"""Mavent compliance tools for Send Agent.

Per Disclosure Desk SOP:
- Go to Tools → Compliance Review → Preview
- All Fail/Alert/Warning must be cleared before sending to borrower
- This is MANDATORY before ordering disclosures
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared import (
    check_mavent_compliance,
    get_mavent_checker,
)

logger = logging.getLogger(__name__)


@tool
def check_mavent(loan_id: str) -> dict:
    """Check Mavent compliance for a loan.
    
    Per SOP: All Fail/Alert/Warning must be cleared before sending.
    This is MANDATORY before ordering disclosures.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with:
        - passed: Whether all checks passed (no issues)
        - has_fails: Whether there are FAIL issues
        - has_alerts: Whether there are ALERT issues
        - has_warnings: Whether there are WARNING issues
        - fails: List of fail issues
        - alerts: List of alert issues
        - warnings: List of warning issues
        - total_issues: Total number of issues
        - blocking: Whether issues block disclosure
        - action: Recommended action
    """
    logger.info(f"[MAVENT] Checking compliance for loan {loan_id[:8]}...")
    
    try:
        result = check_mavent_compliance(loan_id)
        
        if result.get("passed"):
            logger.info("[MAVENT] Compliance check PASSED - no issues")
        else:
            total = result.get("total_issues", 0)
            logger.warning(f"[MAVENT] Compliance check FAILED - {total} issues found")
        
        return result
        
    except Exception as e:
        logger.error(f"[MAVENT] Error checking compliance: {e}")
        return {
            "passed": False,
            "error": str(e),
            "blocking": True,
            "action": "Error checking Mavent compliance - contact support"
        }


@tool
def get_mavent_issues(loan_id: str) -> dict:
    """Get detailed Mavent issues for a loan.
    
    Returns categorized list of all compliance issues.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with categorized issues:
        - fails: List of FAIL issues (most severe)
        - alerts: List of ALERT issues
        - warnings: List of WARNING issues
    """
    logger.info(f"[MAVENT] Getting issues for loan {loan_id[:8]}...")
    
    try:
        result = check_mavent_compliance(loan_id)
        
        return {
            "loan_id": loan_id,
            "fails": result.get("fails", []),
            "alerts": result.get("alerts", []),
            "warnings": result.get("warnings", []),
            "fail_count": len(result.get("fails", [])),
            "alert_count": len(result.get("alerts", [])),
            "warning_count": len(result.get("warnings", [])),
        }
        
    except Exception as e:
        logger.error(f"[MAVENT] Error getting issues: {e}")
        return {
            "loan_id": loan_id,
            "error": str(e),
            "fails": [],
            "alerts": [],
            "warnings": [],
        }


# Export tools for agent registration
mavent_tools = [
    check_mavent,
    get_mavent_issues,
]

