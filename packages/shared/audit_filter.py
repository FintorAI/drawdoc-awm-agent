"""Audit Exception Filter (G16).

Filters audit issues to allow acceptable exceptions before blocking disclosure.

Per SOP Video Notes Lines 214-215:
- Allow specific audit exceptions (e.g., 26.4)
- Allow specific alerts (e.g., HMDA)
- Block on all other audit failures
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# Acceptable audit exceptions (specific error codes that don't block)
ACCEPTABLE_AUDIT_EXCEPTIONS = [
    "26.4",  # Specific exception per SOP
]

# Acceptable alerts (warnings that don't block)
ACCEPTABLE_ALERTS = [
    "HMDA",  # HMDA-related alerts are informational
]


def filter_audit_issues(issues: List[str]) -> Dict[str, any]:
    """Filter out acceptable audit exceptions and alerts.
    
    Args:
        issues: List of audit issue strings
        
    Returns:
        Dictionary with filtered issues and metadata
    """
    if not issues:
        return {
            "blocking_issues": [],
            "acceptable_issues": [],
            "total_issues": 0,
            "has_blocking_issues": False,
        }
    
    blocking_issues = []
    acceptable_issues = []
    
    for issue in issues:
        issue_str = str(issue).strip()
        
        # Check if it's an acceptable exception
        is_acceptable = False
        
        # Check for exception codes
        for exception in ACCEPTABLE_AUDIT_EXCEPTIONS:
            if exception in issue_str:
                acceptable_issues.append(issue_str)
                is_acceptable = True
                logger.info(f"[Audit Filter] Allowing exception: {issue_str}")
                break
        
        # Check for acceptable alerts
        if not is_acceptable:
            for alert in ACCEPTABLE_ALERTS:
                if alert.lower() in issue_str.lower():
                    acceptable_issues.append(issue_str)
                    is_acceptable = True
                    logger.info(f"[Audit Filter] Allowing alert: {issue_str}")
                    break
        
        # If not acceptable, it's blocking
        if not is_acceptable:
            blocking_issues.append(issue_str)
            logger.warning(f"[Audit Filter] Blocking issue: {issue_str}")
    
    result = {
        "blocking_issues": blocking_issues,
        "acceptable_issues": acceptable_issues,
        "total_issues": len(issues),
        "has_blocking_issues": len(blocking_issues) > 0,
    }
    
    if result["has_blocking_issues"]:
        logger.error(f"[Audit Filter] {len(blocking_issues)} blocking issues found")
    else:
        logger.info(f"[Audit Filter] No blocking issues - {len(acceptable_issues)} acceptable issues")
    
    return result


def should_block_on_audit(issues: List[str]) -> bool:
    """Determine if audit issues should block disclosure.
    
    Args:
        issues: List of audit issue strings
        
    Returns:
        True if disclosure should be blocked, False if can proceed
    """
    result = filter_audit_issues(issues)
    return result["has_blocking_issues"]


def get_audit_summary(issues: List[str]) -> str:
    """Get human-readable summary of audit issues.
    
    Args:
        issues: List of audit issue strings
        
    Returns:
        Summary string
    """
    result = filter_audit_issues(issues)
    
    lines = []
    lines.append(f"Total audit issues: {result['total_issues']}")
    
    if result["acceptable_issues"]:
        lines.append(f"✓ Acceptable ({len(result['acceptable_issues'])}): {', '.join(result['acceptable_issues'][:3])}")
        if len(result["acceptable_issues"]) > 3:
            lines.append(f"  ... and {len(result['acceptable_issues']) - 3} more")
    
    if result["blocking_issues"]:
        lines.append(f"✗ BLOCKING ({len(result['blocking_issues'])}): {', '.join(result['blocking_issues'][:3])}")
        if len(result["blocking_issues"]) > 3:
            lines.append(f"  ... and {len(result['blocking_issues']) - 3} more")
    
    return "\n".join(lines)
