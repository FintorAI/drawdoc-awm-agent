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
    AgentStatus,
    RunStatus,
    CreateRunRequest,
    AgentType,
    AGENT_TYPE_SUB_AGENTS,
    SubmitFieldReviewRequest,
    PendingFieldItem,
    FieldDecision,
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


def derive_overall_status(agents: dict, agent_type: AgentType = AgentType.DRAWDOCS) -> RunStatus:
    """
    Derive overall run status from agent statuses.
    
    Rules:
    - Any pending_review → "pending_review" (HIL pause)
    - All success → "success"
    - Any failed → "failed"
    - Any blocked → "blocked" (disclosure)
    - Any running → "running"
    """
    sub_agents = AGENT_TYPE_SUB_AGENTS.get(agent_type, AGENT_TYPE_SUB_AGENTS[AgentType.DRAWDOCS])
    
    statuses = []
    for agent_name in sub_agents:
        agent_data = agents.get(agent_name, {})
        if isinstance(agent_data, dict):
            status = agent_data.get("status", "pending")
        else:
            status = getattr(agent_data, "status", "pending")
        statuses.append(status)
    
    # Check for pending_review (HIL pause) - takes priority
    if any(s == "pending_review" for s in statuses):
        return RunStatus.PENDING_REVIEW
    
    # Check for any blocked (disclosure-specific)
    if any(s == "blocked" for s in statuses):
        return RunStatus.BLOCKED
    
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


def calculate_duration(agents: dict, agent_type: AgentType = AgentType.DRAWDOCS) -> float:
    """Calculate total duration from agent elapsed times."""
    sub_agents = AGENT_TYPE_SUB_AGENTS.get(agent_type, AGENT_TYPE_SUB_AGENTS[AgentType.DRAWDOCS])
    
    total = 0.0
    for agent_name in sub_agents:
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


def build_agent_summary(agents: dict, agent_type: AgentType = AgentType.DRAWDOCS) -> dict[str, AgentStatus]:
    """Build agent summary dict from agents data based on agent type."""
    sub_agents = AGENT_TYPE_SUB_AGENTS.get(agent_type, AGENT_TYPE_SUB_AGENTS[AgentType.DRAWDOCS])
    
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
    
    return {agent_name: get_status(agent_name) for agent_name in sub_agents}


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


def list_all_runs(agent_type_filter: Optional[AgentType] = None) -> list[RunSummary]:
    """
    List all runs from the output directory.
    
    Args:
        agent_type_filter: Optional filter to only return runs of a specific agent type
    
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
        
        # Determine agent type from data (default to drawdocs for backwards compatibility)
        agent_type_str = data.get("agent_type", "drawdocs")
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            agent_type = AgentType.DRAWDOCS
        
        # Apply filter if specified
        if agent_type_filter is not None and agent_type != agent_type_filter:
            continue
        
        agents = data.get("agents", {})
        docs_processed, docs_found = extract_document_counts(agents)
        
        run_summary = RunSummary(
            run_id=run_id,
            loan_id=data.get("loan_id", loan_id),
            agent_type=agent_type,
            status=derive_overall_status(agents, agent_type),
            demo_mode=data.get("demo_mode", True),
            created_at=data.get("execution_timestamp", datetime.fromtimestamp(timestamp).isoformat()),
            duration_seconds=calculate_duration(agents, agent_type),
            documents_processed=docs_processed,
            documents_found=docs_found,
            agents=build_agent_summary(agents, agent_type),
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


def create_run(request: CreateRunRequest) -> tuple[str, AgentType]:
    """
    Create a new run.
    
    Creates initial status file using StatusWriter and spawns agent process in background.
    The initial status file shows the first sub-agent as "running" immediately, allowing
    the frontend to display the run as soon as it starts.
    
    Args:
        request: CreateRunRequest with run configuration
        
    Returns:
        Tuple of (run_id, agent_type)
    """
    # Use StatusWriter to generate run_id and create initial status file
    output_dir = get_output_dir()
    writer = StatusWriter(output_dir)
    
    run_id = writer.generate_run_id(request.loan_id)
    
    # Initialize run with status file - first sub-agent is set to "running" immediately
    writer.initialize_run(
        run_id=run_id,
        loan_id=request.loan_id,
        demo_mode=request.demo_mode,
        document_types=request.document_types,
        max_retries=request.max_retries,
        agent_type=request.agent_type.value,
    )
    
    # Get require_review from request (default True)
    require_review = getattr(request, 'require_review', True)
    
    # Spawn agent process in background
    spawn_agent_process(
        run_id=run_id,
        loan_id=request.loan_id,
        agent_type=request.agent_type,
        demo_mode=request.demo_mode,
        max_retries=request.max_retries,
        document_types=request.document_types,
        require_review=require_review,
    )
    
    return run_id, request.agent_type


def spawn_agent_process(
    run_id: str,
    loan_id: str,
    agent_type: AgentType,
    demo_mode: bool,
    max_retries: int,
    document_types: Optional[list[str]],
    require_review: bool = True,
    resume_from: Optional[str] = None,
) -> None:
    """
    Spawn the agent orchestrator process in the background.
    
    Args:
        run_id: Unique run identifier
        loan_id: Encompass loan GUID
        agent_type: Type of agent pipeline to run
        demo_mode: Whether to run in demo mode
        max_retries: Number of retry attempts
        document_types: Optional list of document types to process
        require_review: If True, pause after prep agent for user review (HIL)
        resume_from: If set, resume from this agent (for continuing after review)
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
        "--agent-type", agent_type.value,
        "--output", str(output_file),
        "--max-retries", str(max_retries),
    ]
    
    if not demo_mode:
        cmd.append("--production")
    
    if document_types:
        cmd.extend(["--document-types", ",".join(document_types)])
    
    if require_review and not resume_from:
        cmd.append("--require-review")
    
    if resume_from:
        cmd.extend(["--resume-from", resume_from])
    
    # Spawn subprocess in background
    # Use subprocess.Popen with stdout/stderr redirected to avoid blocking
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from parent process
        cwd=str(project_root),
    )


# =============================================================================
# HIL (HUMAN-IN-THE-LOOP) REVIEW SERVICES
# =============================================================================

# Field ID to human-readable name mapping (from DrawingDoc Verifications CSV)
FIELD_ID_TO_NAME = {
    "4000": "Borrower First Name",
    "4001": "Borrower Middle Name",
    "4002": "Borrower Last Name",
    "36": "Borrower First/Middle Name",
    "65": "Borrower SSN",
    "66": "Borrower Home Phone",
    "52": "Borrower Marital Status",
    "356": "Appraised Value",
    "745": "Application Date",
    "748": "Closing Date",
    "799": "APR",
    "608": "Amortization Type",
    "1040": "Agency Case #",
    "1240": "Borrower Email",
    "1402": "Borrower DOB",
    # Add more as needed from CSV
}


def get_pending_fields(run_id: str) -> Optional[dict]:
    """
    Get fields pending user review for a run.
    
    Extracts the field mappings from the Prep Agent output and formats
    them for user review.
    
    Args:
        run_id: The run identifier
        
    Returns:
        Dict with pending fields or None if run not found
    """
    file_path = get_run_file_path(run_id)
    data = load_run_data(file_path)
    
    if data is None:
        return None
    
    # Check if run is in pending_review status
    agents = data.get("agents", {})
    prep_data = agents.get("preparation", {})
    prep_status = prep_data.get("status", "pending") if isinstance(prep_data, dict) else getattr(prep_data, "status", "pending")
    
    # For now, allow fetching fields even if not explicitly in pending_review
    # This supports both the new HIL workflow and viewing completed runs
    
    # Extract field mappings from prep output
    prep_output = prep_data.get("output", {}) if isinstance(prep_data, dict) else getattr(prep_data, "output", {})
    if not prep_output:
        return {
            "run_id": run_id,
            "loan_id": data.get("loan_id", ""),
            "status": prep_status,
            "fields": [],
            "total_fields": 0,
            "documents_processed": 0,
        }
    
    # Get field mappings and doc_context
    results = prep_output.get("results", {}) or {}
    field_mappings = results.get("field_mappings", {}) or {}
    doc_context = prep_output.get("doc_context", {}) or {}
    raw_extractions = doc_context.get("raw_extractions", {}) or {}
    extracted_entities = raw_extractions.get("extracted_entities", {}) or {}
    
    # Build list of pending fields
    pending_fields = []
    
    for field_id, field_data in field_mappings.items():
        if isinstance(field_data, dict):
            value = field_data.get("value", "")
            attachment_id = field_data.get("attachment_id", "unknown")
        else:
            value = field_data
            attachment_id = "unknown"
        
        # Find source document from extracted_entities
        source_doc = "Unknown Document"
        for doc_type, doc_data in extracted_entities.items():
            if isinstance(doc_data, dict):
                for extracted_field, extracted_value in doc_data.items():
                    # Check if this extraction matches our field
                    if str(extracted_value) == str(value):
                        source_doc = doc_type
                        break
        
        pending_fields.append(PendingFieldItem(
            field_id=field_id,
            field_name=FIELD_ID_TO_NAME.get(field_id, f"Field {field_id}"),
            extracted_value=value,
            source_document=source_doc,
            attachment_id=attachment_id,
            confidence=None,  # TODO: Add confidence scoring
        ).model_dump())
    
    return {
        "run_id": run_id,
        "loan_id": data.get("loan_id", ""),
        "status": prep_status,
        "fields": pending_fields,
        "total_fields": len(pending_fields),
        "documents_processed": prep_output.get("documents_processed", 0),
    }


def submit_field_review(run_id: str, request: SubmitFieldReviewRequest) -> Optional[dict]:
    """
    Submit user decisions for field review.
    
    Updates the run data with user decisions and optionally continues
    to the next agents.
    
    Args:
        run_id: The run identifier
        request: User decisions for each field
        
    Returns:
        Summary of the review submission or None if run not found
    """
    file_path = get_run_file_path(run_id)
    data = load_run_data(file_path)
    
    if data is None:
        return None
    
    # Process decisions
    accepted_count = 0
    rejected_count = 0
    edited_count = 0
    
    # Get current field mappings
    agents = data.get("agents", {})
    prep_data = agents.get("preparation", {})
    prep_output = prep_data.get("output", {}) if isinstance(prep_data, dict) else getattr(prep_data, "output", {})
    results = prep_output.get("results", {}) or {}
    field_mappings = results.get("field_mappings", {}) or {}
    
    # Track user decisions in a new field
    user_decisions = {}
    approved_fields = {}
    
    for decision in request.decisions:
        field_id = decision.field_id
        
        if decision.decision == FieldDecision.ACCEPT:
            accepted_count += 1
            user_decisions[field_id] = {
                "decision": "accept",
                "original_value": field_mappings.get(field_id, {}).get("value") if isinstance(field_mappings.get(field_id), dict) else field_mappings.get(field_id),
            }
            approved_fields[field_id] = field_mappings.get(field_id)
            
        elif decision.decision == FieldDecision.REJECT:
            rejected_count += 1
            user_decisions[field_id] = {
                "decision": "reject",
                "reason": decision.rejection_reason,
                "original_value": field_mappings.get(field_id, {}).get("value") if isinstance(field_mappings.get(field_id), dict) else field_mappings.get(field_id),
            }
            # Don't include rejected fields in approved_fields
            
        elif decision.decision == FieldDecision.EDIT:
            edited_count += 1
            original = field_mappings.get(field_id, {})
            user_decisions[field_id] = {
                "decision": "edit",
                "original_value": original.get("value") if isinstance(original, dict) else original,
                "edited_value": decision.edited_value,
            }
            # Update the field mapping with edited value
            if isinstance(original, dict):
                approved_fields[field_id] = {
                    **original,
                    "value": decision.edited_value,
                    "edited_by_user": True,
                }
            else:
                approved_fields[field_id] = {
                    "value": decision.edited_value,
                    "edited_by_user": True,
                }
    
    # Store user decisions in the run data
    if "user_review" not in data:
        data["user_review"] = {}
    
    data["user_review"] = {
        "submitted_at": datetime.now().isoformat(),
        "decisions": user_decisions,
        "summary": {
            "accepted": accepted_count,
            "rejected": rejected_count,
            "edited": edited_count,
        },
        "proceed": request.proceed,
    }
    
    # Update the approved field mappings
    if prep_output and "results" in prep_output:
        prep_output["results"]["approved_field_mappings"] = approved_fields
    
    # Update run status based on user decision
    if request.proceed:
        # Continue to next agents - mark prep as success and drawcore as running
        if isinstance(prep_data, dict):
            prep_data["status"] = "success"
        
        # Mark drawcore as running to continue the pipeline
        drawcore_data = agents.get("drawcore", {})
        if isinstance(drawcore_data, dict):
            drawcore_data["status"] = "running"
        
        message = f"Review submitted. Continuing with {accepted_count + edited_count} approved fields."
        
        # Save updated data before spawning process
        save_run_data(file_path, data)
        
        # Spawn continuation process to resume from drawcore
        loan_id = data.get("loan_id", "")
        demo_mode = data.get("demo_mode", True)
        
        # Get document types from config if available
        config = data.get("config", {})
        document_types = config.get("document_types")
        max_retries = config.get("max_retries", 2)
        
        spawn_agent_process(
            run_id=run_id,
            loan_id=loan_id,
            demo_mode=demo_mode,
            max_retries=max_retries,
            document_types=document_types,
            require_review=False,  # Don't pause again
            resume_from="drawcore",  # Resume from drawcore
        )
        
    else:
        # User chose not to proceed - mark run as completed/cancelled
        message = f"Review submitted. Run stopped by user."
        
        # Mark as cancelled
        data["cancelled"] = True
        data["cancelled_at"] = datetime.now().isoformat()
        
        # Save updated data
        save_run_data(file_path, data)
    
    return {
        "success": True,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "edited_count": edited_count,
        "message": message,
    }

