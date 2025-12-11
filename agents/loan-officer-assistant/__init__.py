"""
Loan Officer Assistant (LOA) Agent

An LLM-powered agent that automates Needs List and Gap Analysis generation 
for mortgage loans. The agent retrieves loan context from Encompass, reasons
over requirements from the questionnaire, and generates a prioritized needs list.

Slice 1 (MVP): Loan Context + Data Gap Analysis (Fast Mode)
- Retrieves loan data from Encompass (fields, milestones, eFolder)
- Normalizes to LoanFacts dataclass
- Analyzes data completeness against questionnaire required_fields
- Generates NeedsListResult with gap items

Usage:
    from agents.loan_officer_assistant import run_loan_officer_agent
    
    result = await run_loan_officer_agent("loan-guid-here", mode="fast")
    print(result.summary)

Modes:
    - fast: Data gaps only, skip document processing (~2-5s)
    - full: Data + document gaps, use cached R&S (~5-15s) [Slice 2]
    - refresh_docs: Trigger new R&S job (~30s-5min) [Slice 2]
"""

from .state import (
    # Core data models
    LoanFacts,
    BorrowerFacts,
    PropertyFacts,
    MilestoneInfo,
    EFolderDoc,
    # Gap analysis models
    GapItem,
    GapCategory,
    GapType,
    GapStatus,
    GapSeverity,
    NeedsListResult,
    NeedsListSummary,
    # Agent state
    LOAState,
    LOAResult,
    AgentMode,
    AgentStatus,
    # Write proposals (Slice 4)
    WriteProposal,
)

from .agent import run_loan_officer_agent

__all__ = [
    # Entry point
    "run_loan_officer_agent",
    # Core data models
    "LoanFacts",
    "BorrowerFacts", 
    "PropertyFacts",
    "MilestoneInfo",
    "EFolderDoc",
    # Gap analysis models
    "GapItem",
    "GapCategory",
    "GapType",
    "GapStatus",
    "GapSeverity",
    "NeedsListResult",
    "NeedsListSummary",
    # Agent state
    "LOAState",
    "LOAResult",
    "AgentMode",
    "AgentStatus",
    # Write proposals
    "WriteProposal",
]

__version__ = "0.1.0"

