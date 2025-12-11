"""
Loan Officer Assistant Agent - State Models

This module defines the data models and state schema for the LOA agent.
All dataclasses are designed to be serializable to JSON for LangGraph state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# ENUMS
# =============================================================================

class GapCategory(str, Enum):
    """Categories for gap items, mapped from questionnaire sections."""
    BORROWER = "BORROWER"
    INCOME = "INCOME"
    ASSETS = "ASSETS"
    PROPERTY = "PROPERTY"
    LOAN = "LOAN"
    DOCS = "DOCS"
    RECONCILIATION = "RECONCILIATION"


class GapType(str, Enum):
    """Types of gaps detected."""
    DATA = "DATA"          # Missing or invalid field data
    DOC = "DOC"            # Missing or stale document
    MISMATCH = "MISMATCH"  # Data doesn't match document


class GapStatus(str, Enum):
    """Status of a gap item."""
    MISSING = "MISSING"    # Field/doc not present
    INVALID = "INVALID"    # Field present but invalid
    STALE = "STALE"        # Document too old
    PARTIAL = "PARTIAL"    # Partially complete
    MISMATCH = "MISMATCH"  # Values don't match


class GapSeverity(str, Enum):
    """Severity levels for gaps."""
    CRITICAL = "CRITICAL"  # Blocks loan progress
    WARN = "WARN"          # Needs attention but not blocking
    INFO = "INFO"          # Informational only


class AgentMode(str, Enum):
    """Execution modes for the agent."""
    FAST = "fast"                # Phase 1 only (data gaps)
    FULL = "full"                # Phase 1 + 2 (data + doc gaps)
    REFRESH_DOCS = "refresh_docs"  # Force R&S refresh


class AgentStatus(str, Enum):
    """Agent execution status."""
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


# =============================================================================
# LOAN FACTS MODELS
# =============================================================================

@dataclass
class BorrowerFacts:
    """Normalized borrower data from Encompass."""
    
    borrower_type: str = "PRIMARY"  # "PRIMARY" | "CO_BORROWER"
    
    # Identity
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    ssn: Optional[str] = None
    dob: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    work_phone: Optional[str] = None
    
    # Demographics
    marital_status: Optional[str] = None
    citizenship_status: Optional[str] = None
    dependents_count: Optional[int] = None
    
    # Current Address
    current_address_street: Optional[str] = None
    current_address_city: Optional[str] = None
    current_address_state: Optional[str] = None
    current_address_zip: Optional[str] = None
    years_at_current_address: Optional[float] = None
    
    # Employment
    is_self_employed: Optional[bool] = None
    employer_name: Optional[str] = None
    employer_phone: Optional[str] = None
    employer_address_street: Optional[str] = None
    employer_address_city: Optional[str] = None
    employer_address_state: Optional[str] = None
    employer_address_zip: Optional[str] = None
    job_title: Optional[str] = None
    years_on_job: Optional[float] = None
    months_on_job: Optional[int] = None
    years_in_profession: Optional[float] = None
    
    # Income
    base_income: Optional[float] = None
    overtime_income: Optional[float] = None
    bonus_income: Optional[float] = None
    commission_income: Optional[float] = None
    dividends_income: Optional[float] = None
    rental_income: Optional[float] = None
    other_income: Optional[float] = None
    total_monthly_income: Optional[float] = None
    has_variable_income: Optional[bool] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PropertyFacts:
    """Normalized property data from Encompass."""
    
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None
    
    property_type: Optional[str] = None
    occupancy_type: Optional[str] = None
    number_of_units: Optional[int] = None
    year_built: Optional[int] = None
    
    legal_description: Optional[str] = None
    apn: Optional[str] = None  # Assessor Parcel Number
    
    is_manufactured: Optional[bool] = None
    is_condo: Optional[bool] = None
    condo_project_type: Optional[str] = None
    
    has_hoa: Optional[bool] = None
    monthly_hoa_dues: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class MilestoneInfo:
    """Milestone information from Encompass."""
    
    name: str
    status: str
    status_date: Optional[str] = None
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class EFolderDoc:
    """Document entry from Encompass eFolder."""
    
    attachment_id: str
    title: str
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class LoanFacts:
    """
    Complete normalized loan data from Encompass.
    
    This is the primary context object passed to the gap analyzer.
    """
    
    # Identifiers
    loan_id: str = ""
    loan_number: Optional[str] = None
    
    # Loan Terms
    loan_purpose: Optional[str] = None
    loan_type: Optional[str] = None
    loan_program: Optional[str] = None
    loan_amount: Optional[float] = None
    purchase_price: Optional[float] = None
    appraised_value: Optional[float] = None
    
    # Ratios
    ltv: Optional[float] = None
    cltv: Optional[float] = None
    dti_front: Optional[float] = None
    dti_back: Optional[float] = None
    
    # Terms
    interest_rate: Optional[float] = None
    loan_term_months: Optional[int] = None
    amortization_type: Optional[str] = None
    
    # Down Payment
    down_payment: Optional[float] = None
    down_payment_percent: Optional[float] = None
    cash_to_close: Optional[float] = None
    
    # Dates
    application_date: Optional[str] = None
    estimated_closing_date: Optional[str] = None
    lock_date: Optional[str] = None
    lock_expiration_date: Optional[str] = None
    
    # Borrowers
    borrowers: List[BorrowerFacts] = field(default_factory=list)
    
    # Subject Property
    subject_property: Optional[PropertyFacts] = None
    
    # Milestones
    current_milestone: Optional[str] = None
    milestones: List[MilestoneInfo] = field(default_factory=list)
    
    # eFolder
    efolder_docs: List[EFolderDoc] = field(default_factory=list)
    
    # Loan Officer Info
    lo_name: Optional[str] = None
    lo_email: Optional[str] = None
    lo_nmls: Optional[str] = None
    processor_name: Optional[str] = None
    
    # Credit
    credit_score: Optional[int] = None
    credit_score_date: Optional[str] = None
    
    # Computed
    scenario_tag: str = ""  # e.g., "CONV_PURCHASE_PRIMARY"
    is_mvp_supported: bool = True
    
    # Metadata
    fetch_timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "borrowers":
                result[k] = [b.to_dict() for b in v]
            elif k == "subject_property" and v:
                result[k] = v.to_dict()
            elif k == "milestones":
                result[k] = [m.to_dict() for m in v]
            elif k == "efolder_docs":
                result[k] = [d.to_dict() for d in v]
            else:
                result[k] = v
        return result
    
    @property
    def primary_borrower(self) -> Optional[BorrowerFacts]:
        """Get the primary borrower."""
        for b in self.borrowers:
            if b.borrower_type == "PRIMARY":
                return b
        return self.borrowers[0] if self.borrowers else None
    
    @property
    def co_borrower(self) -> Optional[BorrowerFacts]:
        """Get the co-borrower if present."""
        for b in self.borrowers:
            if b.borrower_type == "CO_BORROWER":
                return b
        return None


# =============================================================================
# GAP ANALYSIS MODELS
# =============================================================================

@dataclass
class GapItem:
    """
    A single gap identified during analysis.
    
    This is the core output unit of the gap analyzer.
    """
    
    id: str  # Unique identifier: e.g., "DATA_borrower_profile_ssn_and_dob_borrower_ssn"
    category: str  # GapCategory value
    type: str  # GapType value
    status: str  # GapStatus value
    severity: str  # GapSeverity value
    
    label: str  # Human-readable label: "Missing: borrower_ssn"
    reason: str  # Why this is required (from questionnaire prompt)
    action: Optional[str] = None  # Recommended action
    
    # For DATA gaps
    field_id: Optional[str] = None  # LoanFacts field path: "borrowers[0].ssn"
    current_value: Optional[Any] = None
    
    # For DOC gaps
    doc_type: Optional[str] = None
    
    # For MISMATCH gaps
    expected_value: Optional[Any] = None
    
    # Source tracking
    section_id: Optional[str] = None
    question_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class NeedsListSummary:
    """Summary statistics for a needs list."""
    
    total: int = 0
    by_status: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    critical_count: int = 0
    warn_count: int = 0
    can_proceed: bool = True
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class NeedsListResult:
    """
    Complete result of gap analysis.
    
    This is the primary output from the gap analyzer.
    """
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    phases_completed: List[str] = field(default_factory=list)  # ["DATA", "DOCS", "RECONCILIATION"]
    items: List[GapItem] = field(default_factory=list)
    summary: Optional[NeedsListSummary] = None
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "phases_completed": self.phases_completed,
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary.to_dict() if self.summary else None,
        }
    
    def compute_summary(self) -> NeedsListSummary:
        """Compute summary statistics from items."""
        summary = NeedsListSummary(total=len(self.items))
        
        for item in self.items:
            # By status
            summary.by_status[item.status] = summary.by_status.get(item.status, 0) + 1
            
            # By severity
            summary.by_severity[item.severity] = summary.by_severity.get(item.severity, 0) + 1
            if item.severity == GapSeverity.CRITICAL.value:
                summary.critical_count += 1
            elif item.severity == GapSeverity.WARN.value:
                summary.warn_count += 1
            
            # By category
            summary.by_category[item.category] = summary.by_category.get(item.category, 0) + 1
            
            # By type
            summary.by_type[item.type] = summary.by_type.get(item.type, 0) + 1
        
        # Can proceed if no critical issues
        summary.can_proceed = summary.critical_count == 0
        
        self.summary = summary
        return summary


# =============================================================================
# LANGGRAPH STATE
# =============================================================================

@dataclass
class LOAState:
    """
    LangGraph state schema for Loan Officer Assistant agent.
    
    This TypedDict-compatible dataclass holds the complete state
    passed between nodes in the LangGraph workflow.
    """
    
    # Inputs
    loan_id: str = ""
    mode: str = AgentMode.FAST.value  # "fast" | "full" | "refresh_docs"
    include_write_proposals: bool = False
    
    # Gathered data
    loan_facts: Optional[Dict] = None  # LoanFacts.to_dict()
    doc_coverage: Optional[Dict] = None  # DocCoverage.to_dict() (Slice 2)
    
    # Analysis results
    needs_list: Optional[Dict] = None  # NeedsListResult.to_dict()
    
    # Outputs
    summary: Optional[str] = None  # LLM-generated summary (Slice 3)
    write_proposals: Optional[List[Dict]] = None  # WriteProposal list (Slice 4)
    
    # Control
    status: str = AgentStatus.RUNNING.value
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for LangGraph state."""
        return self.__dict__.copy()


# =============================================================================
# WRITE PROPOSALS (Slice 4)
# =============================================================================

@dataclass
class WriteProposal:
    """Proposed field update for Encompass."""
    
    field_id: str  # Encompass field ID
    current_value: Any
    proposed_value: Any
    source: str  # Where the proposed value came from
    encompass_field: str  # Encompass field name/description
    approved: bool = False
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()


# =============================================================================
# RESULT MODELS
# =============================================================================

@dataclass
class LOAResult:
    """
    Final result from the LOA agent execution.
    
    This is returned to the caller after the agent completes.
    """
    
    loan_id: str
    execution_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    mode: str = AgentMode.FAST.value
    status: str = AgentStatus.COMPLETE.value
    
    loan_facts: Optional[LoanFacts] = None
    doc_coverage: Optional[Dict] = None  # DocCoverage (Slice 2)
    needs_list: Optional[NeedsListResult] = None
    
    summary: Optional[str] = None  # Human-readable output from LLM
    write_proposals: Optional[List[WriteProposal]] = None
    
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "loan_id": self.loan_id,
            "execution_timestamp": self.execution_timestamp,
            "mode": self.mode,
            "status": self.status,
            "loan_facts": self.loan_facts.to_dict() if self.loan_facts else None,
            "doc_coverage": self.doc_coverage,
            "needs_list": self.needs_list.to_dict() if self.needs_list else None,
            "summary": self.summary,
            "write_proposals": [p.to_dict() for p in self.write_proposals] if self.write_proposals else None,
            "errors": self.errors,
        }

