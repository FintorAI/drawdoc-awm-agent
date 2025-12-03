"""Mavent Compliance Checker for Disclosure Agent.

Per Disclosure Desk SOP:
- Go to Tools → Compliance Review → Preview
- All Fail/Alert/Warning must be cleared before sending to borrower
- This is MANDATORY before ordering disclosures
"""

import logging
import os
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .auth import get_access_token

logger = logging.getLogger(__name__)


# =============================================================================
# API CONFIGURATION
# =============================================================================

# Encompass Compliance Service endpoints
ECS_BASE_PATH = "/ecs/v1"
COMPLIANCE_REPORTS_ENDPOINT = f"{ECS_BASE_PATH}/compliancereports"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComplianceIssue:
    """A single compliance issue (Fail, Alert, or Warning)."""
    
    severity: str  # "Fail", "Alert", "Warning"
    code: Optional[str] = None
    message: Optional[str] = None
    rule_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "rule_name": self.rule_name,
        }


@dataclass
class MaventResult:
    """Result of Mavent compliance check."""
    
    passed: bool
    has_fails: bool = False
    has_alerts: bool = False
    has_warnings: bool = False
    fails: List[ComplianceIssue] = field(default_factory=list)
    alerts: List[ComplianceIssue] = field(default_factory=list)
    warnings: List[ComplianceIssue] = field(default_factory=list)
    report_id: Optional[str] = None
    report_date: Optional[str] = None
    action: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "has_fails": self.has_fails,
            "has_alerts": self.has_alerts,
            "has_warnings": self.has_warnings,
            "fails": [f.to_dict() for f in self.fails],
            "alerts": [a.to_dict() for a in self.alerts],
            "warnings": [w.to_dict() for w in self.warnings],
            "total_issues": len(self.fails) + len(self.alerts) + len(self.warnings),
            "report_id": self.report_id,
            "report_date": self.report_date,
            "action": self.action,
            "error": self.error,
            "blocking": not self.passed,
        }


# =============================================================================
# MAVENT CHECKER CLASS
# =============================================================================

class MaventChecker:
    """Checks Mavent compliance for loans."""
    
    def __init__(self):
        """Initialize Mavent checker."""
        self.api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    def check_compliance(self, loan_id: str) -> MaventResult:
        """Check Mavent compliance for a loan.
        
        Per SOP:
        - All Fail/Alert/Warning must be cleared before sending
        - This is MANDATORY before ordering disclosures
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            MaventResult with compliance status
        """
        logger.info(f"[MAVENT] Checking compliance for loan {loan_id[:8]}...")
        
        try:
            # Get latest compliance report
            report = self._get_latest_report(loan_id)
            
            if report is None:
                logger.info("[MAVENT] No compliance report found - ordering new report")
                report = self._order_compliance_report(loan_id)
            
            if report is None:
                return MaventResult(
                    passed=False,
                    error="Failed to get or order compliance report",
                    action="Unable to check Mavent compliance - contact support"
                )
            
            # Parse issues from report
            fails, alerts, warnings = self._parse_issues(report)
            
            has_fails = len(fails) > 0
            has_alerts = len(alerts) > 0
            has_warnings = len(warnings) > 0
            
            # Determine pass/fail
            if has_fails:
                action = f"Clear {len(fails)} Mavent FAILS before sending - BLOCKING"
                passed = False
            elif has_alerts or has_warnings:
                action = f"Clear {len(alerts)} alerts and {len(warnings)} warnings before sending - BLOCKING"
                passed = False
            else:
                action = None
                passed = True
            
            logger.info(f"[MAVENT] Result: {'PASSED' if passed else 'FAILED'} "
                       f"(Fails: {len(fails)}, Alerts: {len(alerts)}, Warnings: {len(warnings)})")
            
            return MaventResult(
                passed=passed,
                has_fails=has_fails,
                has_alerts=has_alerts,
                has_warnings=has_warnings,
                fails=fails,
                alerts=alerts,
                warnings=warnings,
                report_id=report.get("id"),
                report_date=report.get("createdDate"),
                action=action
            )
            
        except Exception as e:
            logger.error(f"[MAVENT] Error checking compliance: {e}")
            return MaventResult(
                passed=False,
                error=str(e),
                action="Error checking Mavent compliance - see error details"
            )
    
    def _get_latest_report(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest compliance report for a loan.
        
        API: GET /ecs/v1/compliancereports?EntityType=urn:elli:encompass:loan&EntityId={loanId}
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}{COMPLIANCE_REPORTS_ENDPOINT}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",  # or "application/vnd.maventxml" for XML
        }
        
        params = {
            "EntityType": "urn:elli:encompass:loan",
            "EntityId": loan_id
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            
            reports = response.json()
            
            # Return latest report (should be first in list)
            if reports and len(reports) > 0:
                return reports[0]
            
            return None
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # No report found
                return None
            logger.error(f"[MAVENT] API error getting report: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[MAVENT] Error getting report: {e}")
            raise
    
    def _order_compliance_report(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """Order a new compliance report.
        
        API: POST /ecs/v1/ComplianceReports
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}{COMPLIANCE_REPORTS_ENDPOINT}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "entity": {
                "entityType": "urn:elli:encompass:loan",
                "entityId": loan_id
            },
            "reportType": "review",
            "reportMode": "manual",
            "skipAudit": "true",
            "channelName": "retail",
            "reviewSource": "retail"
        }
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=120)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"[MAVENT] Error ordering report: {e}")
            return None
    
    def _parse_issues(self, report: Dict[str, Any]) -> tuple:
        """Parse compliance issues from report.
        
        Returns:
            Tuple of (fails, alerts, warnings) lists
        """
        fails = []
        alerts = []
        warnings = []
        
        # Parse issues from report structure
        # Note: Actual structure depends on API response format
        issues = report.get("issues", []) or report.get("results", [])
        
        for issue in issues:
            severity = issue.get("severity", "").upper()
            
            compliance_issue = ComplianceIssue(
                severity=severity,
                code=issue.get("code"),
                message=issue.get("message") or issue.get("description"),
                rule_name=issue.get("ruleName") or issue.get("rule"),
            )
            
            if severity == "FAIL" or severity == "FAILURE":
                fails.append(compliance_issue)
            elif severity == "ALERT":
                alerts.append(compliance_issue)
            elif severity == "WARNING":
                warnings.append(compliance_issue)
        
        return fails, alerts, warnings


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_checker: Optional[MaventChecker] = None


def get_mavent_checker() -> MaventChecker:
    """Get the Mavent checker singleton."""
    global _checker
    if _checker is None:
        _checker = MaventChecker()
    return _checker


def check_mavent_compliance(loan_id: str) -> Dict[str, Any]:
    """Check Mavent compliance for a loan.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with compliance results
    """
    checker = get_mavent_checker()
    result = checker.check_compliance(loan_id)
    return result.to_dict()

