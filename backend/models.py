"""
Pydantic models for the Multi-Agent Dashboard API.

These models define the request/response shapes for the API endpoints.
Supports multiple agent types: DrawDocs, Disclosure, and LOA.
"""

from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class AgentType(str, Enum):
    """Type of agent pipeline."""
    DRAWDOCS = "drawdocs"
    DISCLOSURE = "disclosure"
    LOA = "loa"


class AgentStatus(str, Enum):
    """Status of an individual agent."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"  # For disclosure when blocked by compliance


class RunStatus(str, Enum):
    """Overall run status."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"  # For disclosure when blocked by compliance


# =============================================================================
# AGENT TYPE CONFIGURATIONS
# =============================================================================

# Sub-agents for each agent type
AGENT_TYPE_SUB_AGENTS = {
    AgentType.DRAWDOCS: ["preparation", "drawcore", "verification", "orderdocs"],
    AgentType.DISCLOSURE: ["verification", "preparation", "send"],
    AgentType.LOA: ["verification", "generation", "delivery"],  # Placeholder for future
}


# =============================================================================
# REQUEST MODELS
# =============================================================================

class CreateRunRequest(BaseModel):
    """Request body for POST /api/runs."""
    loan_id: str = Field(..., description="Encompass loan GUID (required)")
    agent_type: AgentType = Field(default=AgentType.DRAWDOCS, description="Type of agent pipeline to run")
    demo_mode: bool = Field(default=True, description="Demo mode: no actual writes to Encompass")
    max_retries: int = Field(default=2, ge=0, le=5, description="Number of retry attempts per agent")
    # DrawDocs-specific fields
    document_types: Optional[list[str]] = Field(
        default=None,
        description="Optional list of document types to process (DrawDocs only). null = process all documents"
    )
    # Disclosure/LOA-specific fields
    lo_email: Optional[str] = Field(
        default=None,
        description="Loan officer email address (required for Disclosure and LOA agents)"
    )


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class DrawDocsAgentSummary(BaseModel):
    """Summary of DrawDocs agent statuses (4 sub-agents)."""
    preparation: AgentStatus = AgentStatus.PENDING
    drawcore: AgentStatus = AgentStatus.PENDING
    verification: AgentStatus = AgentStatus.PENDING
    orderdocs: AgentStatus = AgentStatus.PENDING


class DisclosureAgentSummary(BaseModel):
    """Summary of Disclosure agent statuses (3 sub-agents)."""
    verification: AgentStatus = AgentStatus.PENDING
    preparation: AgentStatus = AgentStatus.PENDING
    send: AgentStatus = AgentStatus.PENDING


class LOAAgentSummary(BaseModel):
    """Summary of LOA agent statuses (3 sub-agents) - placeholder."""
    verification: AgentStatus = AgentStatus.PENDING
    generation: AgentStatus = AgentStatus.PENDING
    delivery: AgentStatus = AgentStatus.PENDING


class RunSummary(BaseModel):
    """Summary of a run for the list endpoint."""
    run_id: str
    loan_id: str
    agent_type: AgentType = AgentType.DRAWDOCS
    status: RunStatus
    demo_mode: bool
    created_at: str
    duration_seconds: float
    documents_processed: int
    documents_found: int
    # Flexible agents dict - structure depends on agent_type
    agents: dict[str, AgentStatus]


class CreateRunResponse(BaseModel):
    """Response from POST /api/runs."""
    run_id: str
    agent_type: AgentType


# =============================================================================
# INTERNAL MODELS (for file storage)
# =============================================================================

class AgentResult(BaseModel):
    """Result from an individual agent."""
    status: AgentStatus = AgentStatus.PENDING
    attempts: int = 0
    elapsed_seconds: float = 0.0
    output: Optional[Any] = None
    error: Optional[str] = None


class RunData(BaseModel):
    """Complete run data stored in JSON file."""
    loan_id: str
    execution_timestamp: str
    agent_type: AgentType = AgentType.DRAWDOCS
    demo_mode: bool = True
    summary: dict = Field(default_factory=dict)
    agents: dict[str, AgentResult] = Field(default_factory=dict)
    # Disclosure-specific fields
    blocking_issues: list[str] = Field(default_factory=list)
    tracking_id: Optional[str] = None
    
    @classmethod
    def create_initial(cls, loan_id: str, agent_type: AgentType = AgentType.DRAWDOCS, demo_mode: bool = True) -> "RunData":
        """Create initial run data with running status based on agent type."""
        sub_agents = AGENT_TYPE_SUB_AGENTS.get(agent_type, AGENT_TYPE_SUB_AGENTS[AgentType.DRAWDOCS])
        
        # First sub-agent starts as running, rest are pending
        agents = {}
        for i, agent_name in enumerate(sub_agents):
            if i == 0:
                agents[agent_name] = AgentResult(status=AgentStatus.RUNNING)
            else:
                agents[agent_name] = AgentResult(status=AgentStatus.PENDING)
        
        return cls(
            loan_id=loan_id,
            execution_timestamp=datetime.now().isoformat(),
            agent_type=agent_type,
            demo_mode=demo_mode,
            agents=agents,
        )

