"""
Services for managing agent runs.

Handles file I/O and business logic for the runs API.
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import (
    RunData,
    RunSummary,
    AgentSummary,
    AgentStatus,
    RunStatus,
    CreateRunRequest,
)

# Add project root to path for status_writer import
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.status_writer import StatusWriter


def get_output_dir() -> Path:
    """Get the output directory from environment variable or default.
    
    Handles relative paths by resolving them against the backend directory,
    ensuring consistency between backend and spawned agent processes.
    So OUTPUT_DIR=./output becomes backend/output.
    """
    backend_dir = Path(__file__).parent
    output_dir = os.environ.get("OUTPUT_DIR")
    if output_dir:
        path = Path(output_dir)
        # If relative path, resolve against backend directory
        if not path.is_absolute():
            path = backend_dir / path
    else:
        # Default to backend/output
        path = backend_dir / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_run_file_path(run_id: str) -> Path:
    """Get the file path for a run."""
    return get_output_dir() / f"{run_id}_results.json"


def parse_run_id(filename: str) -> Optional[tuple[str, str, int]]:
    """
    Parse run_id from filename.
    
    Expected format: {loan_id}_{timestamp}_results.json
    
    Returns:
        Tuple of (run_id, loan_id, timestamp) or None if invalid
    """
    if not filename.endswith("_results.json"):
        return None
    
    # Remove _results.json suffix
    base = filename[:-13]
    
    # Split to extract loan_id and timestamp
    # Format: uuid_timestamp where uuid has format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    parts = base.rsplit("_", 1)
    if len(parts) != 2:
        return None
    
    loan_id, timestamp_str = parts
    
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return None
    
    return (base, loan_id, timestamp)


def derive_overall_status(agents: dict) -> RunStatus:
    """
    Derive overall run status from agent statuses.
    
    Rules:
    - All success → "success"
    - Any failed → "failed"
    - Any running → "running"
    """
    statuses = []
    for agent_name in ["preparation", "verification", "orderdocs"]:
        agent_data = agents.get(agent_name, {})
        if isinstance(agent_data, dict):
            status = agent_data.get("status", "pending")
        else:
            status = getattr(agent_data, "status", "pending")
        statuses.append(status)
    
    # Check for any failed
    if any(s == "failed" for s in statuses):
        return RunStatus.FAILED
    
    # Check for any running
    if any(s == "running" for s in statuses):
        return RunStatus.RUNNING
    
    # Check if all success
    if all(s == "success" for s in statuses):
        return RunStatus.SUCCESS
    
    # Default to running if some are pending
    return RunStatus.RUNNING


def calculate_duration(agents: dict) -> float:
    """Calculate total duration from agent elapsed times."""
    total = 0.0
    for agent_name in ["preparation", "verification", "orderdocs"]:
        agent_data = agents.get(agent_name, {})
        if isinstance(agent_data, dict):
            elapsed = agent_data.get("elapsed_seconds", 0) or 0
        else:
            elapsed = getattr(agent_data, "elapsed_seconds", 0) or 0
        total += float(elapsed)
    return round(total, 2)


def extract_document_counts(agents: dict) -> tuple[int, int]:
    """Extract documents_processed and documents_found from preparation output."""
    prep_data = agents.get("preparation", {})
    if isinstance(prep_data, dict):
        output = prep_data.get("output", {}) or {}
    else:
        output = getattr(prep_data, "output", {}) or {}
    
    if isinstance(output, dict):
        docs_processed = output.get("documents_processed", 0) or 0
        docs_found = output.get("total_documents_found", 0) or 0
    else:
        docs_processed = 0
        docs_found = 0
    
    return (docs_processed, docs_found)


def build_agent_summary(agents: dict) -> AgentSummary:
    """Build agent summary from agents dict."""
    def get_status(agent_name: str) -> AgentStatus:
        agent_data = agents.get(agent_name, {})
        if isinstance(agent_data, dict):
            status_str = agent_data.get("status", "pending")
        else:
            status_str = getattr(agent_data, "status", "pending")
        
        try:
            return AgentStatus(status_str)
        except ValueError:
            return AgentStatus.PENDING
    
    return AgentSummary(
        preparation=get_status("preparation"),
        verification=get_status("verification"),
        orderdocs=get_status("orderdocs"),
    )


def load_run_data(file_path: Path) -> Optional[dict]:
    """Load run data from JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        return None


def save_run_data(file_path: Path, data: dict) -> None:
    """Save run data to JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def list_all_runs() -> list[RunSummary]:
    """
    List all runs from the output directory.
    
    Returns:
        List of RunSummary objects sorted by created_at descending
    """
    output_dir = get_output_dir()
    runs = []
    
    if not output_dir.exists():
        return runs
    
    for file_path in output_dir.glob("*_results.json"):
        parsed = parse_run_id(file_path.name)
        if not parsed:
            continue
        
        run_id, loan_id, timestamp = parsed
        
        # Load run data
        data = load_run_data(file_path)
        if not data:
            continue
        
        agents = data.get("agents", {})
        docs_processed, docs_found = extract_document_counts(agents)
        
        run_summary = RunSummary(
            run_id=run_id,
            loan_id=data.get("loan_id", loan_id),
            status=derive_overall_status(agents),
            demo_mode=data.get("demo_mode", True),
            created_at=data.get("execution_timestamp", datetime.fromtimestamp(timestamp).isoformat()),
            duration_seconds=calculate_duration(agents),
            documents_processed=docs_processed,
            documents_found=docs_found,
            agents=build_agent_summary(agents),
        )
        runs.append(run_summary)
    
    # Sort by created_at descending
    runs.sort(key=lambda r: r.created_at, reverse=True)
    
    return runs


def get_run_detail(run_id: str) -> Optional[dict]:
    """
    Get full run detail for a specific run.
    
    Args:
        run_id: The run identifier (format: {loan_id}_{timestamp})
        
    Returns:
        Complete run data dict or None if not found
    """
    file_path = get_run_file_path(run_id)
    return load_run_data(file_path)


def create_run(request: CreateRunRequest) -> str:
    """
    Create a new run.
    
    Creates initial status file using StatusWriter and spawns agent process in background.
    The initial status file shows preparation as "running" immediately, allowing
    the frontend to display the run as soon as it starts.
    
    Args:
        request: CreateRunRequest with run configuration
        
    Returns:
        The generated run_id
    """
    # Use StatusWriter to generate run_id and create initial status file
    output_dir = get_output_dir()
    writer = StatusWriter(output_dir)
    
    run_id = writer.generate_run_id(request.loan_id)
    
    # Initialize run with status file - preparation is set to "running" immediately
    writer.initialize_run(
        run_id=run_id,
        loan_id=request.loan_id,
        demo_mode=request.demo_mode,
        document_types=request.document_types,
        max_retries=request.max_retries,
    )
    
    # Spawn agent process in background
    spawn_agent_process(
        run_id=run_id,
        loan_id=request.loan_id,
        demo_mode=request.demo_mode,
        max_retries=request.max_retries,
        document_types=request.document_types,
    )
    
    return run_id


def spawn_agent_process(
    run_id: str,
    loan_id: str,
    demo_mode: bool,
    max_retries: int,
    document_types: Optional[list[str]],
) -> None:
    """
    Spawn the agent orchestrator process in the background.
    
    Args:
        run_id: Unique run identifier
        loan_id: Encompass loan GUID
        demo_mode: Whether to run in demo mode
        max_retries: Number of retry attempts
        document_types: Optional list of document types to process
    """
    # Get paths
    project_root = Path(__file__).parent.parent
    runner_script = project_root / "backend" / "agent_runner.py"
    output_file = get_run_file_path(run_id)
    
    # Build command
    cmd = [
        sys.executable,
        str(runner_script),
        "--loan-id", loan_id,
        "--output", str(output_file),
        "--max-retries", str(max_retries),
    ]
    
    if not demo_mode:
        cmd.append("--production")
    
    if document_types:
        cmd.extend(["--document-types", ",".join(document_types)])
    
    # Spawn subprocess in background
    # Use subprocess.Popen with stdout/stderr redirected to avoid blocking
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from parent process
        cwd=str(project_root),
    )

