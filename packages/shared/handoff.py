"""Handoff schemas for disclosure to draw docs communication.

This module defines the data structures used when disclosure
hands off to draw docs workflow.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class DisclosureHandoff:
    """Data passed from Disclosure to Draw Docs workflow.
    
    This schema defines what information Disclosure provides to Draw Docs
    when a loan is ready for document drawing.
    
    Attributes:
        loan_id: Encompass loan GUID
        cd_status: CD status ("CD Approved", "Pending", etc.)
        cd_ack_date: Date borrower acknowledged CD
        waiting_period_ends: Date when 3-day waiting period ends
        is_mvp_supported: Whether loan is MVP eligible (Conventional, NV/CA)
        loan_type: Loan type (Conventional, FHA, VA, USDA)
        property_state: Property state abbreviation
        mi_calculated: MI calculation result (if applicable)
        tolerance_issues: List of fee tolerance violations (flagged, not cured)
        fields_verified: Count of fields verified
        fields_missing: List of fields still missing
        disclosure_timestamp: When disclosure was completed
        requires_manual: Whether manual processing is required
        manual_reasons: List of reasons for manual processing
    """
    
    loan_id: str
    cd_status: str = "Pending"
    cd_ack_date: Optional[date] = None
    waiting_period_ends: Optional[date] = None
    is_mvp_supported: bool = True
    loan_type: str = "Unknown"
    property_state: Optional[str] = None
    mi_calculated: Optional[Dict[str, Any]] = None
    tolerance_issues: List[str] = field(default_factory=list)
    fields_verified: int = 0
    fields_missing: List[str] = field(default_factory=list)
    disclosure_timestamp: Optional[datetime] = None
    requires_manual: bool = False
    manual_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "loan_id": self.loan_id,
            "cd_status": self.cd_status,
            "cd_ack_date": self.cd_ack_date.isoformat() if self.cd_ack_date else None,
            "waiting_period_ends": self.waiting_period_ends.isoformat() if self.waiting_period_ends else None,
            "is_mvp_supported": self.is_mvp_supported,
            "loan_type": self.loan_type,
            "property_state": self.property_state,
            "mi_calculated": self.mi_calculated,
            "tolerance_issues": self.tolerance_issues,
            "fields_verified": self.fields_verified,
            "fields_missing": self.fields_missing,
            "disclosure_timestamp": self.disclosure_timestamp.isoformat() if self.disclosure_timestamp else None,
            "requires_manual": self.requires_manual,
            "manual_reasons": self.manual_reasons,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DisclosureHandoff":
        """Create from dictionary."""
        return cls(
            loan_id=data.get("loan_id", ""),
            cd_status=data.get("cd_status", "Pending"),
            cd_ack_date=date.fromisoformat(data["cd_ack_date"]) if data.get("cd_ack_date") else None,
            waiting_period_ends=date.fromisoformat(data["waiting_period_ends"]) if data.get("waiting_period_ends") else None,
            is_mvp_supported=data.get("is_mvp_supported", True),
            loan_type=data.get("loan_type", "Unknown"),
            property_state=data.get("property_state"),
            mi_calculated=data.get("mi_calculated"),
            tolerance_issues=data.get("tolerance_issues", []),
            fields_verified=data.get("fields_verified", 0),
            fields_missing=data.get("fields_missing", []),
            disclosure_timestamp=datetime.fromisoformat(data["disclosure_timestamp"]) if data.get("disclosure_timestamp") else None,
            requires_manual=data.get("requires_manual", False),
            manual_reasons=data.get("manual_reasons", []),
        )
    
    def is_ready_for_draw_docs(self) -> bool:
        """Check if loan is ready for Draw Docs processing.
        
        Returns:
            True if CD is approved, acknowledged, and waiting period complete
        """
        if self.requires_manual:
            return False
        
        if self.cd_status != "CD Approved":
            return False
        
        if self.cd_ack_date is None:
            return False
        
        if self.waiting_period_ends is not None:
            if date.today() < self.waiting_period_ends:
                return False
        
        return True
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary.
        
        Returns:
            Summary string
        """
        lines = [f"Disclosure Handoff for Loan {self.loan_id}"]
        lines.append("-" * 40)
        lines.append(f"CD Status: {self.cd_status}")
        lines.append(f"Loan Type: {self.loan_type}")
        lines.append(f"State: {self.property_state or 'Unknown'}")
        lines.append(f"MVP Supported: {self.is_mvp_supported}")
        
        if self.cd_ack_date:
            lines.append(f"CD Acknowledged: {self.cd_ack_date}")
        if self.waiting_period_ends:
            lines.append(f"Waiting Period Ends: {self.waiting_period_ends}")
        
        lines.append(f"Fields Verified: {self.fields_verified}")
        lines.append(f"Fields Missing: {len(self.fields_missing)}")
        
        if self.mi_calculated:
            if self.mi_calculated.get("requires_mi"):
                lines.append(f"MI Monthly: ${self.mi_calculated.get('monthly_amount', 0):.2f}")
            else:
                lines.append("MI: Not required")
        
        if self.tolerance_issues:
            lines.append(f"Tolerance Issues: {len(self.tolerance_issues)}")
        
        if self.requires_manual:
            lines.append("\n⚠️ REQUIRES MANUAL PROCESSING:")
            for reason in self.manual_reasons:
                lines.append(f"  - {reason}")
        
        lines.append("-" * 40)
        lines.append(f"Ready for Draw Docs: {self.is_ready_for_draw_docs()}")
        
        return "\n".join(lines)


def create_handoff_from_results(
    loan_id: str,
    verification_results: Dict[str, Any],
    preparation_results: Dict[str, Any],
    request_results: Optional[Dict[str, Any]] = None,
) -> DisclosureHandoff:
    """Create DisclosureHandoff from agent results.
    
    Args:
        loan_id: Encompass loan GUID
        verification_results: Results from verification agent
        preparation_results: Results from preparation agent
        request_results: Results from request agent (optional)
        
    Returns:
        DisclosureHandoff instance
    """
    # Extract data from results
    is_mvp_supported = verification_results.get("is_mvp_supported", True)
    loan_type = verification_results.get("loan_type", "Unknown")
    property_state = verification_results.get("property_state")
    mvp_warnings = verification_results.get("mvp_warnings", [])
    
    fields_verified = verification_results.get("fields_checked", 0)
    fields_missing = verification_results.get("fields_missing", [])
    
    mi_result = preparation_results.get("mi_result")
    tolerance_result = preparation_results.get("tolerance_result", {})
    
    # Build tolerance issues list
    tolerance_issues = []
    if tolerance_result.get("has_violations"):
        tolerance_issues.append(f"Cure needed: ${tolerance_result.get('total_cure_needed', 0):.2f}")
    
    # Determine if manual processing required
    requires_manual = False
    manual_reasons = []
    
    if not is_mvp_supported:
        requires_manual = True
        manual_reasons.extend(mvp_warnings)
    
    if tolerance_result.get("has_violations"):
        requires_manual = True
        manual_reasons.append("Fee tolerance violations require review")
    
    return DisclosureHandoff(
        loan_id=loan_id,
        cd_status="Pending",  # Would be updated based on actual CD status
        is_mvp_supported=is_mvp_supported,
        loan_type=loan_type,
        property_state=property_state,
        mi_calculated=mi_result,
        tolerance_issues=tolerance_issues,
        fields_verified=fields_verified,
        fields_missing=fields_missing,
        disclosure_timestamp=datetime.now(),
        requires_manual=requires_manual,
        manual_reasons=manual_reasons,
    )

