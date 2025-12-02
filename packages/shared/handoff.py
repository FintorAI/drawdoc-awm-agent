"""Handoff schemas for agent pipeline communication.

This module defines the data structures used when:
1. Disclosure Agent hands off to Draw Docs workflow (after CD ACK + 3-day wait)
2. Initial LE → COC/LE → CD transitions within Disclosure Agent

v2 Architecture: Supports both LE and CD handoffs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DisclosureType(str, Enum):
    """Type of disclosure being processed."""
    INITIAL_LE = "initial_le"      # Initial Loan Estimate (within 3 days of app)
    COC_LE = "coc_le"              # Change of Circumstances / Revised LE
    INITIAL_CD = "initial_cd"      # Initial Closing Disclosure
    REVISED_CD = "revised_cd"      # Revised Closing Disclosure


class HandoffStatus(str, Enum):
    """Status of the handoff."""
    PENDING = "pending"            # Waiting for acknowledgment
    LE_SENT = "le_sent"            # LE sent, awaiting intent to proceed
    CD_SENT = "cd_sent"            # CD sent, in 3-day waiting period
    CD_APPROVED = "cd_approved"    # CD approved and acknowledged
    READY_FOR_DRAW = "ready"       # Ready for Draw Docs
    BLOCKED = "blocked"            # Cannot proceed - requires manual intervention


@dataclass
class DisclosureHandoff:
    """Data passed between agent pipelines.
    
    Used for:
    1. Initial LE → COC/LE transition (internal to Disclosure Agent)
    2. Disclosure → Draw Docs handoff (after CD approved + 3-day wait)
    
    Attributes:
        loan_id: Encompass loan GUID
        disclosure_type: Type of disclosure (initial_le, coc_le, initial_cd, revised_cd)
        status: Current handoff status
        
        # Timing
        le_sent_date: Date Initial LE was sent
        le_ack_date: Date borrower acknowledged LE (intent to proceed)
        cd_sent_date: Date CD was sent
        cd_ack_date: Date borrower acknowledged CD
        waiting_period_ends: Date when 3-day TRID waiting period ends
        
        # Loan metadata
        is_mvp_supported: Whether loan is MVP eligible (Conventional, NV/CA)
        loan_type: Loan type (Conventional, FHA, VA, USDA)
        property_state: Property state abbreviation
        
        # Results from disclosure processing
        mi_calculated: MI calculation result (if applicable)
        tolerance_issues: List of fee tolerance violations
        fields_verified: Count of fields verified
        fields_missing: List of fields still missing
        blocking_issues: List of blocking issues
        warnings: List of non-blocking warnings
        
        # Timestamps
        disclosure_timestamp: When disclosure was completed
        
        # Manual processing
        requires_manual: Whether manual processing is required
        manual_reasons: List of reasons for manual processing
    """
    
    loan_id: str
    disclosure_type: str = DisclosureType.INITIAL_LE.value
    status: str = HandoffStatus.PENDING.value
    
    # Timing fields
    le_sent_date: Optional[date] = None
    le_ack_date: Optional[date] = None
    cd_sent_date: Optional[date] = None
    cd_ack_date: Optional[date] = None
    waiting_period_ends: Optional[date] = None
    
    # Loan metadata
    is_mvp_supported: bool = True
    loan_type: str = "Unknown"
    property_state: Optional[str] = None
    
    # Results
    mi_calculated: Optional[Dict[str, Any]] = None
    tolerance_issues: List[str] = field(default_factory=list)
    fields_verified: int = 0
    fields_missing: List[str] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Timestamps
    disclosure_timestamp: Optional[datetime] = None
    
    # Manual processing
    requires_manual: bool = False
    manual_reasons: List[str] = field(default_factory=list)
    
    # Legacy compatibility (v1 fields)
    cd_status: str = "Pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "loan_id": self.loan_id,
            "disclosure_type": self.disclosure_type,
            "status": self.status,
            "le_sent_date": self.le_sent_date.isoformat() if self.le_sent_date else None,
            "le_ack_date": self.le_ack_date.isoformat() if self.le_ack_date else None,
            "cd_sent_date": self.cd_sent_date.isoformat() if self.cd_sent_date else None,
            "cd_ack_date": self.cd_ack_date.isoformat() if self.cd_ack_date else None,
            "waiting_period_ends": self.waiting_period_ends.isoformat() if self.waiting_period_ends else None,
            "is_mvp_supported": self.is_mvp_supported,
            "loan_type": self.loan_type,
            "property_state": self.property_state,
            "mi_calculated": self.mi_calculated,
            "tolerance_issues": self.tolerance_issues,
            "fields_verified": self.fields_verified,
            "fields_missing": self.fields_missing,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "disclosure_timestamp": self.disclosure_timestamp.isoformat() if self.disclosure_timestamp else None,
            "requires_manual": self.requires_manual,
            "manual_reasons": self.manual_reasons,
            "cd_status": self.cd_status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DisclosureHandoff":
        """Create from dictionary."""
        return cls(
            loan_id=data.get("loan_id", ""),
            disclosure_type=data.get("disclosure_type", DisclosureType.INITIAL_LE.value),
            status=data.get("status", HandoffStatus.PENDING.value),
            le_sent_date=date.fromisoformat(data["le_sent_date"]) if data.get("le_sent_date") else None,
            le_ack_date=date.fromisoformat(data["le_ack_date"]) if data.get("le_ack_date") else None,
            cd_sent_date=date.fromisoformat(data["cd_sent_date"]) if data.get("cd_sent_date") else None,
            cd_ack_date=date.fromisoformat(data["cd_ack_date"]) if data.get("cd_ack_date") else None,
            waiting_period_ends=date.fromisoformat(data["waiting_period_ends"]) if data.get("waiting_period_ends") else None,
            is_mvp_supported=data.get("is_mvp_supported", True),
            loan_type=data.get("loan_type", "Unknown"),
            property_state=data.get("property_state"),
            mi_calculated=data.get("mi_calculated"),
            tolerance_issues=data.get("tolerance_issues", []),
            fields_verified=data.get("fields_verified", 0),
            fields_missing=data.get("fields_missing", []),
            blocking_issues=data.get("blocking_issues", []),
            warnings=data.get("warnings", []),
            disclosure_timestamp=datetime.fromisoformat(data["disclosure_timestamp"]) if data.get("disclosure_timestamp") else None,
            requires_manual=data.get("requires_manual", False),
            manual_reasons=data.get("manual_reasons", []),
            cd_status=data.get("cd_status", "Pending"),
        )
    
    def is_ready_for_draw_docs(self) -> bool:
        """Check if loan is ready for Draw Docs processing.
        
        Requirements:
        1. CD is approved and acknowledged
        2. 3-day TRID waiting period has passed
        3. No manual intervention required
        
        Returns:
            True if ready for Draw Docs
        """
        if self.requires_manual:
            return False
        
        if self.status == HandoffStatus.BLOCKED.value:
            return False
        
        # For Draw Docs: Need CD approved + 3-day wait complete
        if self.cd_status != "CD Approved" and self.status != HandoffStatus.READY_FOR_DRAW.value:
            return False
        
        if self.cd_ack_date is None:
            return False
        
        if self.waiting_period_ends is not None:
            if date.today() < self.waiting_period_ends:
                return False
        
        return True
    
    def is_le_complete(self) -> bool:
        """Check if Initial LE process is complete.
        
        Returns:
            True if LE has been sent
        """
        return self.le_sent_date is not None
    
    def needs_coc_le(self) -> bool:
        """Check if a Change of Circumstances / Revised LE is needed.
        
        Returns:
            True if COC LE processing is required
        """
        # If initial LE was sent and there are changes requiring revised LE
        if not self.is_le_complete():
            return False
        
        # Check if COC triggers exist (would be set by verification agent)
        return "COC required" in self.warnings
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary.
        
        Returns:
            Summary string
        """
        lines = [f"Disclosure Handoff for Loan {self.loan_id}"]
        lines.append("=" * 50)
        lines.append(f"Type: {self.disclosure_type}")
        lines.append(f"Status: {self.status}")
        lines.append(f"Loan Type: {self.loan_type}")
        lines.append(f"State: {self.property_state or 'Unknown'}")
        lines.append(f"MVP Supported: {self.is_mvp_supported}")
        
        lines.append("\n--- Timing ---")
        if self.le_sent_date:
            lines.append(f"LE Sent: {self.le_sent_date}")
        if self.le_ack_date:
            lines.append(f"LE Acknowledged: {self.le_ack_date}")
        if self.cd_sent_date:
            lines.append(f"CD Sent: {self.cd_sent_date}")
        if self.cd_ack_date:
            lines.append(f"CD Acknowledged: {self.cd_ack_date}")
        if self.waiting_period_ends:
            lines.append(f"Waiting Period Ends: {self.waiting_period_ends}")
        
        lines.append("\n--- Verification ---")
        lines.append(f"Fields Verified: {self.fields_verified}")
        lines.append(f"Fields Missing: {len(self.fields_missing)}")
        
        if self.mi_calculated:
            if self.mi_calculated.get("requires_mi"):
                lines.append(f"MI Monthly: ${self.mi_calculated.get('monthly_amount', 0):.2f}")
            else:
                lines.append("MI: Not required")
        
        if self.blocking_issues:
            lines.append("\n⛔ BLOCKING ISSUES:")
            for issue in self.blocking_issues:
                lines.append(f"  - {issue}")
        
        if self.warnings:
            lines.append("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        if self.tolerance_issues:
            lines.append(f"\n💰 Tolerance Issues: {len(self.tolerance_issues)}")
        
        if self.requires_manual:
            lines.append("\n🔧 REQUIRES MANUAL PROCESSING:")
            for reason in self.manual_reasons:
                lines.append(f"  - {reason}")
        
        lines.append("\n" + "=" * 50)
        lines.append(f"Ready for Draw Docs: {self.is_ready_for_draw_docs()}")
        
        return "\n".join(lines)


def create_handoff_from_results(
    loan_id: str,
    disclosure_type: str = DisclosureType.INITIAL_LE.value,
    verification_results: Optional[Dict[str, Any]] = None,
    preparation_results: Optional[Dict[str, Any]] = None,
    send_results: Optional[Dict[str, Any]] = None,
    pre_check_results: Optional[Dict[str, Any]] = None,
) -> DisclosureHandoff:
    """Create DisclosureHandoff from agent results.
    
    Args:
        loan_id: Encompass loan GUID
        disclosure_type: Type of disclosure (initial_le, coc_le, cd)
        verification_results: Results from verification agent
        preparation_results: Results from preparation agent
        send_results: Results from send agent
        pre_check_results: Results from pre-check
        
    Returns:
        DisclosureHandoff instance
    """
    verification_results = verification_results or {}
    preparation_results = preparation_results or {}
    send_results = send_results or {}
    pre_check_results = pre_check_results or {}
    
    # Extract data from results
    is_mvp_supported = verification_results.get("is_mvp_supported", True)
    loan_type = verification_results.get("loan_type", "Unknown")
    property_state = verification_results.get("property_state")
    
    fields_verified = verification_results.get("fields_checked", 0)
    fields_missing = verification_results.get("fields_missing", [])
    blocking_issues = verification_results.get("blocking_issues", [])
    
    mi_result = preparation_results.get("mi_result")
    
    # Combine warnings from all sources
    warnings = []
    warnings.extend(verification_results.get("warnings", []))
    warnings.extend(preparation_results.get("warnings", []))
    warnings.extend(pre_check_results.get("warnings", []))
    
    # Build tolerance issues list
    tolerance_issues = []
    tolerance_result = preparation_results.get("tolerance_result", {})
    if tolerance_result.get("has_violations"):
        tolerance_issues.append(f"Cure needed: ${tolerance_result.get('total_cure_needed', 0):.2f}")
    
    # Determine status
    status = HandoffStatus.PENDING.value
    if blocking_issues:
        status = HandoffStatus.BLOCKED.value
    elif send_results.get("order_success"):
        if disclosure_type in [DisclosureType.INITIAL_LE.value, DisclosureType.COC_LE.value]:
            status = HandoffStatus.LE_SENT.value
        else:
            status = HandoffStatus.CD_SENT.value
    
    # Determine if manual processing required
    requires_manual = False
    manual_reasons = []
    
    if not is_mvp_supported:
        requires_manual = True
        manual_reasons.extend(verification_results.get("mvp_warnings", []))
    
    if blocking_issues:
        requires_manual = True
        manual_reasons.append("Has blocking issues")
    
    if tolerance_result.get("has_violations"):
        manual_reasons.append("Fee tolerance violations require review")
    
    # Get dates from send results
    le_sent_date = None
    cd_sent_date = None
    
    if send_results.get("order_success"):
        sent_date = date.today()
        if disclosure_type in [DisclosureType.INITIAL_LE.value, DisclosureType.COC_LE.value]:
            le_sent_date = sent_date
        else:
            cd_sent_date = sent_date
    
    return DisclosureHandoff(
        loan_id=loan_id,
        disclosure_type=disclosure_type,
        status=status,
        le_sent_date=le_sent_date,
        cd_sent_date=cd_sent_date,
        is_mvp_supported=is_mvp_supported,
        loan_type=loan_type,
        property_state=property_state,
        mi_calculated=mi_result,
        tolerance_issues=tolerance_issues,
        fields_verified=fields_verified,
        fields_missing=fields_missing,
        blocking_issues=blocking_issues,
        warnings=warnings,
        disclosure_timestamp=datetime.now(),
        requires_manual=requires_manual,
        manual_reasons=manual_reasons,
    )
