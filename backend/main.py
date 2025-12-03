"""
Multi-Agent Dashboard API

FastAPI application for managing multi-agent runs (DrawDocs, Disclosure, LOA).

Endpoints:
- GET /api/runs - List all runs (with optional agent_type filter)
- GET /api/runs/{run_id} - Get run detail
- POST /api/runs - Start a new run
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CreateRunRequest, CreateRunResponse, RunSummary, AgentType,
    SubmitFieldReviewRequest, SubmitFieldReviewResponse, PendingFieldsResponse
)
from services import (
    list_all_runs, get_run_detail, create_run,
    get_pending_fields, submit_field_review
)


# =============================================================================
# APP CONFIGURATION
# =============================================================================

app = FastAPI(
    title="Multi-Agent Dashboard API",
    description="API for managing DrawDocs, Disclosure, and LOA agent runs",
    version="2.0.0",
)

# CORS configuration - allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# =============================================================================
# RUNS API ENDPOINTS
# =============================================================================

@app.get("/api/runs", response_model=list[RunSummary])
async def get_runs(
    agent_type: Optional[AgentType] = Query(
        default=None,
        description="Filter runs by agent type (drawdocs, disclosure, loa)"
    )
):
    """
    Get list of all runs (in-progress and completed).
    
    Args:
        agent_type: Optional filter to only return runs of a specific agent type
    
    Returns:
        List of run summaries sorted by created_at descending
    """
    return list_all_runs(agent_type_filter=agent_type)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """
    Get full run detail for a specific run.
    
    Args:
        run_id: The run identifier (format: {loan_id}_{timestamp})
        
    Returns:
        Complete run data (full test_results.json contents)
        
    Raises:
        404: Run not found
    """
    run_data = get_run_detail(run_id)
    
    if run_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found"
        )
    
    return run_data


@app.post("/api/runs", response_model=CreateRunResponse)
async def start_run(request: CreateRunRequest):
    """
    Start a new agent run.
    
    Creates initial status file and spawns agent process in background.
    Returns immediately with the run_id and agent_type.
    
    Args:
        request: Run configuration (includes agent_type)
        
    Returns:
        Object containing the generated run_id and agent_type
    """
    run_id, agent_type = create_run(request)
    return CreateRunResponse(run_id=run_id, agent_type=agent_type)


# =============================================================================
# HIL (HUMAN-IN-THE-LOOP) REVIEW ENDPOINTS
# =============================================================================

@app.get("/api/runs/{run_id}/pending-fields", response_model=PendingFieldsResponse)
async def get_run_pending_fields(run_id: str):
    """
    Get fields pending user review for a run.
    
    Returns the extracted fields from the Prep Agent that need user approval
    before the Drawcore Agent writes them to Encompass.
    
    Args:
        run_id: The run identifier
        
    Returns:
        List of pending fields with their extracted values and source documents
        
    Raises:
        404: Run not found
        400: Run is not in pending_review status
    """
    result = get_pending_fields(run_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found"
        )
    
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
    
    return result


@app.post("/api/runs/{run_id}/review", response_model=SubmitFieldReviewResponse)
async def submit_run_review(run_id: str, request: SubmitFieldReviewRequest):
    """
    Submit user decisions for field review.
    
    After reviewing the extracted fields, the user can:
    - Accept: Use the extracted value as-is
    - Reject: Skip writing this field (with optional reason)
    - Edit: Use a modified value instead
    
    After submission, the run continues to the next agents if `proceed=True`.
    
    Args:
        run_id: The run identifier
        request: Field decisions and whether to proceed
        
    Returns:
        Summary of accepted/rejected/edited fields
        
    Raises:
        404: Run not found
        400: Run is not in pending_review status
    """
    result = submit_field_review(run_id, request)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found"
        )
    
    if not result.get("success", False) and "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
    
    return result


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
    )

