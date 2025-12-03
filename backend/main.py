"""
DrawDoc Agent API

FastAPI application for managing agent runs.

Endpoints:
- GET /api/runs - List all runs
- GET /api/runs/{run_id} - Get run detail
- POST /api/runs - Start a new run
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import CreateRunRequest, CreateRunResponse, RunSummary
from services import list_all_runs, get_run_detail, create_run


# =============================================================================
# APP CONFIGURATION
# =============================================================================

app = FastAPI(
    title="DrawDoc Agent API",
    description="API for managing DrawDoc verification agent runs",
    version="1.0.0",
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
async def get_runs():
    """
    Get list of all runs (in-progress and completed).
    
    Returns:
        List of run summaries sorted by created_at descending
    """
    return list_all_runs()


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
    Returns immediately with the run_id.
    
    Args:
        request: Run configuration
        
    Returns:
        Object containing the generated run_id
    """
    run_id = create_run(request)
    return CreateRunResponse(run_id=run_id)


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

