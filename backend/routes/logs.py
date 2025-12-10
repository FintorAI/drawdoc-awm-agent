"""API endpoints for accessing disclosure agent logs.

For frontend timeline display.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.shared.logging_config import get_recent_logs, get_agent_timeline

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent")
async def get_logs(
    loan_id: Optional[str] = Query(None, description="Filter by loan ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries")
):
    """Get recent log entries.
    
    Query Parameters:
    - loan_id: Optional loan GUID to filter logs
    - limit: Maximum number of entries (1-1000)
    
    Returns:
        List of log entry objects
    """
    try:
        logs = get_recent_logs(loan_id=loan_id, limit=limit)
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{loan_id}")
async def get_timeline(loan_id: str):
    """Get structured timeline for a specific loan.
    
    Path Parameters:
    - loan_id: Loan GUID
    
    Returns:
        Timeline data structured by agent
    """
    try:
        timeline = get_agent_timeline(loan_id)
        return {
            "success": True,
            "timeline": timeline
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{loan_id}/{agent_name}")
async def get_agent_logs(
    loan_id: str,
    agent_name: str
):
    """Get logs for a specific agent and loan.
    
    Path Parameters:
    - loan_id: Loan GUID
    - agent_name: Agent identifier
    
    Returns:
        Filtered log entries for the specified agent
    """
    try:
        valid_agents = ["ORCHESTRATOR", "VERIFICATION", "PREPARATION", "SEND", "SYSTEM"]
        agent_name_upper = agent_name.upper()
        
        if agent_name_upper not in valid_agents:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent name. Must be one of: {', '.join(valid_agents)}"
            )
        
        # Get all logs for the loan
        all_logs = get_recent_logs(loan_id=loan_id, limit=1000)
        
        # Filter by agent
        agent_logs = [log for log in all_logs if log.get("agent") == agent_name_upper]
        
        return {
            "success": True,
            "agent": agent_name_upper,
            "loan_id": loan_id,
            "count": len(agent_logs),
            "logs": agent_logs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

