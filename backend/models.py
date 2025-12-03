"""
Pydantic models for the DrawDoc Agent API.

These models define the request/response shapes for the API endpoints.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class AgentStatus(str, Enum):
    """Status of an individual agent."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class RunStatus(str, Enum):
    """Overall run status."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# =============================================================================
# REQUEST MODELS
# =============================================================================

class CreateRunRequest(BaseModel):
    """Request body for POST /api/runs."""
    loan_id: str = Field(..., description="Encompass loan GUID (required)")
    demo_mode: bool = Field(default=True, description="Demo mode: no actual writes to Encompass")
    max_retries: int = Field(default=2, ge=0, le=5, description="Number of retry attempts per agent")
    document_types: Optional[list[str]] = Field(
        default=None,
        description="Optional list of document types to process. null = process all documents"
    )


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class AgentSummary(BaseModel):
    """Summary of agent statuses in a run."""
    preparation: AgentStatus = AgentStatus.PENDING
    drawcore: AgentStatus = AgentStatus.PENDING
    verification: AgentStatus = AgentStatus.PENDING
    orderdocs: AgentStatus = AgentStatus.PENDING


class RunSummary(BaseModel):
    """Summary of a run for the list endpoint."""
    run_id: str
    loan_id: str
    status: RunStatus
    demo_mode: bool
    created_at: str
    duration_seconds: float
    documents_processed: int
    documents_found: int
    agents: AgentSummary


class CreateRunResponse(BaseModel):
    """Response from POST /api/runs."""
    run_id: str


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
    demo_mode: bool = True
    summary: dict = Field(default_factory=dict)
    agents: dict[str, AgentResult] = Field(default_factory=dict)
    
    @classmethod
    def create_initial(cls, loan_id: str, demo_mode: bool = True) -> "RunData":
        """Create initial run data with running status."""
        return cls(
            loan_id=loan_id,
            execution_timestamp=datetime.now().isoformat(),
            demo_mode=demo_mode,
            agents={
                "preparation": AgentResult(status=AgentStatus.RUNNING),
                "drawcore": AgentResult(status=AgentStatus.PENDING),
                "verification": AgentResult(status=AgentStatus.PENDING),
                "orderdocs": AgentResult(status=AgentStatus.PENDING),
            }
        )

