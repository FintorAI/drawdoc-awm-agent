"""Audit filtering tools for send agent.

Implements G16: Audit exception filtering.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.audit_filter import filter_audit_issues

logger = logging.getLogger(__name__)


@tool
def filter_audit_exceptions(audit_issues: List[str]) -> dict:
    """Filter audit exceptions to allow acceptable ones (G16).
    
    Per GAPS.md G16 and SOP Video Notes Lines 218-220:
    - Exception 26.4 is acceptable (allow)
    - HMDA alerts are acceptable (allow)
    - Other exceptions should block disclosure
    
    Args:
        audit_issues: List of audit issues/exceptions from Encompass
        
    Returns:
        Dictionary with filtered audit results
    """
    logger.info(f"[G16] Filtering {len(audit_issues)} audit issues...")
    
    result = filter_audit_issues(audit_issues)
    
    if result.get("should_block"):
        logger.warning(f"[G16] {len(result['blocking_issues'])} blocking issues found")
    else:
        logger.info(f"[G16] All audit issues are acceptable")
    
    return result


@tool
def check_loan_audit_status(loan_id: str, audit_issues: List[str] = None) -> dict:
    """Check audit status for a loan (G16).
    
    Per GAPS.md G16:
    - Fetch audit issues from Encompass
    - Filter using acceptable exception list
    - Return whether disclosure should be blocked
    
    Args:
        loan_id: Encompass loan GUID
        audit_issues: Optional list of audit issues (if not provided, would need to fetch)
        
    Returns:
        Dictionary with audit check results
    """
    logger.info(f"[G16] Checking audit status for loan {loan_id[:8]}...")
    
    result = check_audit_exceptions(loan_id, audit_issues)
    
    return result


# Export tools
audit_tools = [
    filter_audit_exceptions,
    check_loan_audit_status,
]

