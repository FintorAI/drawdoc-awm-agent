"""
Status Writer - Manages run status files for multi-agent orchestrators.

This utility class handles:
- Initializing run status files when a run starts
- Updating agent status as each sub-agent progresses
- Finalizing runs when complete

Supports multiple agent types:
- DrawDocs: preparation → drawcore → verification → orderdocs
- Disclosure: verification → preparation → send
- LOA: verification → generation → delivery

File naming convention:
- Status files: {OUTPUT_DIR}/{run_id}_results.json
- run_id format: {loan_id}_{unix_timestamp}

Status transitions per agent:
- "pending" → "running" (when agent starts)
- "running" → "success" (when agent completes successfully)
- "running" → "failed" (when agent errors after all retries)
- "running" → "blocked" (for disclosure when compliance blocks)
- "running" → "pending_review" (HIL: waiting for user to review/approve fields)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# Agent type configurations
AGENT_TYPE_SUB_AGENTS = {
    "drawdocs": ["preparation", "drawcore", "verification", "orderdocs"],
    "disclosure": ["verification", "preparation", "send"],
    "loa": ["verification", "generation", "delivery"],
}


class StatusWriter:
    """
    Manages run status files for live frontend updates.
    
    Usage:
        writer = StatusWriter(output_dir="/path/to/output")
        
        # Initialize run
        run_id = writer.generate_run_id(loan_id)
        writer.initialize_run(run_id, loan_id, demo_mode=True, agent_type="drawdocs")
        
        # Update agent status
        writer.update_agent_status(run_id, "preparation", "running")
        writer.update_agent_status(run_id, "preparation", "success", 
                                   elapsed_seconds=35.25, output={...})
        
        # Finalize run
        writer.finalize_run(run_id)
    """
    
    # Default agent names (DrawDocs) - kept for backwards compatibility
    AGENTS = ["preparation", "drawcore", "verification", "orderdocs"]
    
    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the status writer.
        
        Args:
            output_dir: Directory for status files. Defaults to OUTPUT_DIR env var
                       or backend/output relative to project root.
                       
        Note: Relative paths are resolved against the project root to ensure
        consistency between backend and spawned agent processes.
        """
        # Project root and backend directory for resolving paths
        project_root = Path(__file__).parent.parent.parent
        backend_dir = project_root / "backend"
        
        if output_dir:
            self.output_dir = Path(output_dir)
        elif os.environ.get("OUTPUT_DIR"):
            self.output_dir = Path(os.environ["OUTPUT_DIR"])
        else:
            # Default: backend/output
            self.output_dir = backend_dir / "output"
        
        # If relative path, resolve against backend directory
        # So OUTPUT_DIR=./output becomes backend/output
        if not self.output_dir.is_absolute():
            self.output_dir = backend_dir / self.output_dir
        
        # Ensure directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"StatusWriter initialized with output_dir: {self.output_dir}")
    
    def generate_run_id(self, loan_id: str) -> str:
        """
        Generate a unique run ID.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            run_id in format: {loan_id}_{unix_timestamp}
        """
        timestamp = int(datetime.now().timestamp())
        return f"{loan_id}_{timestamp}"
    
    def get_file_path(self, run_id: str) -> Path:
        """Get the file path for a run's status file."""
        return self.output_dir / f"{run_id}_results.json"
    
    def initialize_run(
        self,
        run_id: str,
        loan_id: str,
        demo_mode: bool = True,
        document_types: Optional[list] = None,
        max_retries: int = 2,
        agent_type: str = "drawdocs",
    ) -> Dict[str, Any]:
        """
        Initialize a run status file.
        
        Creates the initial status JSON immediately when run starts.
        The first sub-agent is set to "running" status.
        
        Args:
            run_id: Unique run identifier
            loan_id: Encompass loan GUID
            demo_mode: Whether running in demo mode (no writes to Encompass)
            document_types: Optional list of document types to process
            max_retries: Number of retry attempts per agent
            agent_type: Type of agent pipeline ("drawdocs", "disclosure", "loa")
            
        Returns:
            The initial status data dict
        """
        # Get sub-agents for this agent type
        sub_agents = AGENT_TYPE_SUB_AGENTS.get(agent_type, AGENT_TYPE_SUB_AGENTS["drawdocs"])
        
        # Build agents dict - first agent is running, rest are pending
        agents = {}
        for i, agent_name in enumerate(sub_agents):
            agents[agent_name] = {
                "status": "running" if i == 0 else "pending",
                "attempts": 0,
                "elapsed_seconds": 0,
                "output": None,
                "error": None,
            }
        
        initial_data = {
            "loan_id": loan_id,
            "run_id": run_id,
            "agent_type": agent_type,
            "execution_timestamp": datetime.now().isoformat(),
            "demo_mode": demo_mode,
            "config": {
                "document_types": document_types,
                "max_retries": max_retries,
            },
            "summary": {},
            "agents": agents,
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "agent": "orchestrator",
                    "message": f"Starting {agent_type} orchestrator for loan {loan_id}",
                }
            ],
            "progress": {
                "documents_found": 0,
                "documents_processed": 0,
                "fields_extracted": 0,
                "current_document": None,
            },
            # Disclosure-specific fields (safe to include for all types)
            "blocking_issues": [],
            "tracking_id": None,
        }
        
        # Update instance agents list to match this run's agent type
        self._current_agents = sub_agents
        
        # Write to file
        file_path = self.get_file_path(run_id)
        self._write_json(file_path, initial_data)
        
        logger.info(f"Initialized {agent_type} run status file: {file_path.name}")
        return initial_data
    
    def update_agent_status(
        self,
        run_id: str,
        agent_name: str,
        status: str,
        attempts: Optional[int] = None,
        elapsed_seconds: Optional[float] = None,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        set_next_running: bool = True,
    ) -> Dict[str, Any]:
        """
        Update a specific agent's status in the run file.
        
        Args:
            run_id: Unique run identifier
            agent_name: Name of agent ("preparation", "drawcore", "verification", "orderdocs")
            status: New status ("pending", "running", "success", "failed", "pending_review")
            attempts: Number of attempts made (optional)
            elapsed_seconds: Time taken in seconds (optional)
            output: Agent output data (optional)
            error: Error message if failed (optional)
            set_next_running: If status is "success", set next agent to "running"
            
        Returns:
            The updated status data dict
        """
        file_path = self.get_file_path(run_id)
        data = self._read_json(file_path)
        
        if not data:
            logger.error(f"Cannot update agent status - file not found: {file_path}")
            return {}
        
        # Update the specific agent
        if agent_name not in data.get("agents", {}):
            data.setdefault("agents", {})[agent_name] = {}
        
        agent_data = data["agents"][agent_name]
        agent_data["status"] = status
        
        if attempts is not None:
            agent_data["attempts"] = attempts
        if elapsed_seconds is not None:
            agent_data["elapsed_seconds"] = round(elapsed_seconds, 2)
        if output is not None:
            agent_data["output"] = output
        if error is not None:
            agent_data["error"] = error
        
        # If agent succeeded and set_next_running is True, set next agent to "running"
        if status == "success" and set_next_running:
            # Get the agents list for this run (from file data or default)
            agent_type = data.get("agent_type", "drawdocs")
            agents_list = AGENT_TYPE_SUB_AGENTS.get(agent_type, self.AGENTS)
            
            agent_idx = agents_list.index(agent_name) if agent_name in agents_list else -1
            if agent_idx >= 0 and agent_idx < len(agents_list) - 1:
                next_agent = agents_list[agent_idx + 1]
                if data["agents"].get(next_agent, {}).get("status") == "pending":
                    data["agents"][next_agent]["status"] = "running"
                    logger.debug(f"Set {next_agent} status to 'running'")
        
        # Write updated data
        self._write_json(file_path, data)
        
        logger.info(f"Updated {agent_name} status to '{status}' in {file_path.name}")
        return data
    
    def mark_agent_running(self, run_id: str, agent_name: str) -> Dict[str, Any]:
        """
        Mark an agent as running.
        
        Convenience method for transitioning agent from pending to running.
        
        Args:
            run_id: Unique run identifier
            agent_name: Name of agent
            
        Returns:
            The updated status data dict
        """
        return self.update_agent_status(
            run_id=run_id,
            agent_name=agent_name,
            status="running",
            set_next_running=False,
        )
    
    def mark_agent_success(
        self,
        run_id: str,
        agent_name: str,
        attempts: int,
        elapsed_seconds: float,
        output: Any,
    ) -> Dict[str, Any]:
        """
        Mark an agent as successfully completed.
        
        Convenience method for marking agent success and setting next to running.
        
        Args:
            run_id: Unique run identifier
            agent_name: Name of agent
            attempts: Number of attempts made
            elapsed_seconds: Time taken
            output: Agent output data
            
        Returns:
            The updated status data dict
        """
        return self.update_agent_status(
            run_id=run_id,
            agent_name=agent_name,
            status="success",
            attempts=attempts,
            elapsed_seconds=elapsed_seconds,
            output=output,
            error=None,
            set_next_running=True,
        )
    
    def mark_agent_failed(
        self,
        run_id: str,
        agent_name: str,
        attempts: int,
        elapsed_seconds: float,
        error: str,
    ) -> Dict[str, Any]:
        """
        Mark an agent as failed.
        
        Args:
            run_id: Unique run identifier
            agent_name: Name of agent
            attempts: Number of attempts made
            elapsed_seconds: Time taken before failure
            error: Error message
            
        Returns:
            The updated status data dict
        """
        return self.update_agent_status(
            run_id=run_id,
            agent_name=agent_name,
            status="failed",
            attempts=attempts,
            elapsed_seconds=elapsed_seconds,
            output=None,
            error=error,
            set_next_running=False,
        )
    
    def mark_agent_pending_review(
        self,
        run_id: str,
        agent_name: str,
        attempts: int,
        elapsed_seconds: float,
        output: Any,
    ) -> Dict[str, Any]:
        """
        Mark an agent as pending review (HIL - Human in the Loop).
        
        This status indicates the agent has completed extraction but is
        waiting for user review before proceeding to write fields.
        
        Args:
            run_id: Unique run identifier
            agent_name: Name of agent
            attempts: Number of attempts made
            elapsed_seconds: Time taken
            output: Agent output data (extracted fields)
            
        Returns:
            The updated status data dict
        """
        return self.update_agent_status(
            run_id=run_id,
            agent_name=agent_name,
            status="pending_review",
            attempts=attempts,
            elapsed_seconds=elapsed_seconds,
            output=output,
            error=None,
            set_next_running=False,  # Don't auto-start next agent
        )
    
    def add_log(
        self,
        run_id: str,
        message: str,
        level: str = "info",
        agent: Optional[str] = None,
        event_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a log entry to the run's logs array.
        
        Args:
            run_id: Unique run identifier
            message: Log message (human-readable)
            level: Log level ("info", "warning", "error", "success")
            agent: Agent name (optional, defaults to "orchestrator")
            event_type: Type of event for filtering (e.g., "agent_start", "document", "field", "correction")
            details: Additional structured data for the event
            
        Returns:
            The updated status data dict
        """
        file_path = self.get_file_path(run_id)
        data = self._read_json(file_path)
        
        if not data:
            logger.error(f"Cannot add log - file not found: {file_path}")
            return {}
        
        # Ensure logs array exists
        if "logs" not in data:
            data["logs"] = []
        
        # Add new log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "agent": agent or "orchestrator",
            "message": message,
        }
        
        if event_type:
            log_entry["event_type"] = event_type
        if details:
            log_entry["details"] = details
        
        data["logs"].append(log_entry)
        
        # Keep only the last 50 logs to prevent file bloat
        if len(data["logs"]) > 50:
            data["logs"] = data["logs"][-50:]
        
        self._write_json(file_path, data)
        return data
    
    def update_progress(
        self,
        run_id: str,
        documents_found: Optional[int] = None,
        documents_processed: Optional[int] = None,
        fields_extracted: Optional[int] = None,
        current_document: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the progress section with live metrics.
        
        Args:
            run_id: Unique run identifier
            documents_found: Total documents found (set once)
            documents_processed: Number of documents processed so far
            fields_extracted: Number of fields extracted so far
            current_document: Name of document currently being processed
            
        Returns:
            The updated status data dict
        """
        file_path = self.get_file_path(run_id)
        data = self._read_json(file_path)
        
        if not data:
            logger.error(f"Cannot update progress - file not found: {file_path}")
            return {}
        
        # Ensure progress section exists
        if "progress" not in data:
            data["progress"] = {
                "documents_found": 0,
                "documents_processed": 0,
                "fields_extracted": 0,
                "current_document": None,
            }
        
        # Update only the provided fields
        if documents_found is not None:
            data["progress"]["documents_found"] = documents_found
        if documents_processed is not None:
            data["progress"]["documents_processed"] = documents_processed
        if fields_extracted is not None:
            data["progress"]["fields_extracted"] = fields_extracted
        if current_document is not None:
            data["progress"]["current_document"] = current_document
        
        self._write_json(file_path, data)
        return data
    
    # =========================================================================
    # STRUCTURED LOG HELPERS
    # =========================================================================
    
    def log_agent_start(self, run_id: str, agent_name: str) -> Dict[str, Any]:
        """Log when an agent starts processing."""
        return self.add_log(
            run_id=run_id,
            message=f"Starting {agent_name.title()} agent...",
            level="info",
            agent=agent_name,
            event_type="agent_start",
        )
    
    def log_agent_complete(
        self, 
        run_id: str, 
        agent_name: str, 
        elapsed_seconds: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log when an agent completes."""
        if success:
            return self.add_log(
                run_id=run_id,
                message=f"{agent_name.title()} completed in {elapsed_seconds:.1f}s",
                level="success",
                agent=agent_name,
                event_type="agent_complete",
                details={"elapsed_seconds": elapsed_seconds},
            )
        else:
            return self.add_log(
                run_id=run_id,
                message=f"{agent_name.title()} failed: {error or 'Unknown error'}",
                level="error",
                agent=agent_name,
                event_type="agent_failed",
                details={"elapsed_seconds": elapsed_seconds, "error": error},
            )
    
    def log_document_processing(
        self, 
        run_id: str, 
        doc_name: str, 
        doc_type: str,
        status: str = "processing",
    ) -> Dict[str, Any]:
        """Log document processing events."""
        if status == "processing":
            message = f"Processing: {doc_name}"
        elif status == "success":
            message = f"Extracted: {doc_name}"
        elif status == "error":
            message = f"Failed: {doc_name}"
        else:
            message = f"{status}: {doc_name}"
            
        return self.add_log(
            run_id=run_id,
            message=message,
            level="info" if status != "error" else "warning",
            agent="preparation",
            event_type="document",
            details={"document_name": doc_name, "document_type": doc_type, "status": status},
        )
    
    def log_fields_extracted(
        self, 
        run_id: str, 
        doc_name: str,
        field_count: int,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Log when fields are extracted from a document."""
        return self.add_log(
            run_id=run_id,
            message=f"Extracted {field_count} fields from {doc_name}",
            level="info",
            agent="preparation",
            event_type="fields_extracted",
            details={"document_name": doc_name, "field_count": field_count, "fields": fields},
        )
    
    def log_field_correction(
        self,
        run_id: str,
        field_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log when a field correction is identified."""
        return self.add_log(
            run_id=run_id,
            message=f"Correction: {field_name} → {str(new_value)[:30]}{'...' if len(str(new_value)) > 30 else ''}",
            level="info",
            agent="verification",
            event_type="correction",
            details={
                "field_id": field_id,
                "field_name": field_name,
                "old_value": str(old_value)[:50],
                "new_value": str(new_value)[:50],
                "reason": reason,
            },
        )
    
    def log_verification_summary(
        self,
        run_id: str,
        corrections_count: int,
        fields_checked: int,
    ) -> Dict[str, Any]:
        """Log verification summary."""
        return self.add_log(
            run_id=run_id,
            message=f"Found {corrections_count} corrections in {fields_checked} fields",
            level="info",
            agent="verification",
            event_type="verification_summary",
            details={"corrections_count": corrections_count, "fields_checked": fields_checked},
        )
    
    def log_drawcore_summary(
        self,
        run_id: str,
        phases_completed: int,
        total_phases: int,
        fields_updated: int,
        fields_failed: int,
    ) -> Dict[str, Any]:
        """Log drawcore summary."""
        return self.add_log(
            run_id=run_id,
            message=f"Completed {phases_completed}/{total_phases} phases, {fields_updated} fields updated, {fields_failed} failed",
            level="info",
            agent="drawcore",
            event_type="drawcore_summary",
            details={
                "phases_completed": phases_completed,
                "total_phases": total_phases,
                "fields_updated": fields_updated,
                "fields_failed": fields_failed,
            },
        )
    
    def log_orderdocs_summary(
        self,
        run_id: str,
        total_fields: int,
        fields_with_values: int,
        corrections_applied: int,
    ) -> Dict[str, Any]:
        """Log orderdocs summary."""
        return self.add_log(
            run_id=run_id,
            message=f"Checked {total_fields} fields, {fields_with_values} have values, {corrections_applied} corrections applied",
            level="info",
            agent="orderdocs",
            event_type="orderdocs_summary",
            details={
                "total_fields": total_fields,
                "fields_with_values": fields_with_values,
                "corrections_applied": corrections_applied,
            },
        )
    
    def finalize_run(
        self,
        run_id: str,
        summary: Optional[Dict[str, Any]] = None,
        summary_text: Optional[str] = None,
        json_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Finalize a run by adding summary information.
        
        Adds:
        - summary: Custom summary dict
        - summary_text: Human-readable summary
        - overall_status: Derived from agent statuses
        - total_duration_seconds: Sum of agent elapsed times
        - completed_at: ISO timestamp when run completed (useful for analytics)
        
        Args:
            run_id: Unique run identifier
            summary: Summary dict to add
            summary_text: Human-readable summary text
            json_output: Structured JSON output (if different from main data)
            
        Returns:
            The finalized status data dict
        """
        file_path = self.get_file_path(run_id)
        data = self._read_json(file_path)
        
        if not data:
            logger.error(f"Cannot finalize run - file not found: {file_path}")
            return {}
        
        if summary:
            data["summary"] = summary
        
        if summary_text:
            data["summary_text"] = summary_text
        
        if json_output:
            data["json_output"] = json_output
        
        # Get agent type for status calculation
        agent_type = data.get("agent_type", "drawdocs")
        
        # Calculate overall status
        data["overall_status"] = self._derive_overall_status(data.get("agents", {}), agent_type)
        
        # Calculate total duration
        data["total_duration_seconds"] = self._calculate_duration(data.get("agents", {}), agent_type)
        
        # Add completion timestamp (useful for debugging/analytics)
        data["completed_at"] = datetime.now().isoformat()
        
        # Write final data
        self._write_json(file_path, data)
        
        logger.info(f"Finalized run: {file_path.name}")
        return data
    
    def get_run_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Read the current run data.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Current run data dict or None if not found
        """
        file_path = self.get_file_path(run_id)
        return self._read_json(file_path)
    
    def _read_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None
    
    def _write_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        Write JSON to file atomically.
        
        Uses a temporary file + rename pattern to prevent corrupted JSON
        if the process crashes mid-write. The rename operation is atomic
        on most filesystems (POSIX).
        """
        try:
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            temp_path.replace(file_path)  # Atomic on most filesystems
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")
            # Clean up temp file if it exists
            try:
                temp_path = file_path.with_suffix('.tmp')
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            raise
    
    def _derive_overall_status(self, agents: Dict[str, Any], agent_type: str = "drawdocs") -> str:
        """
        Derive overall run status from agent statuses.
        
        Rules:
        - Any blocked → "blocked" (disclosure-specific)
        - Any failed → "failed"
        - Any running → "running"
        - All success → "success"
        - Otherwise → "running" (some pending)
        """
        agents_list = AGENT_TYPE_SUB_AGENTS.get(agent_type, self.AGENTS)
        statuses = [
            agents.get(name, {}).get("status", "pending")
            for name in agents_list
        ]
        
        if any(s == "blocked" for s in statuses):
            return "blocked"
        if any(s == "failed" for s in statuses):
            return "failed"
        if any(s == "running" for s in statuses):
            return "running"
        if all(s == "success" for s in statuses):
            return "success"
        return "running"
    
    def _calculate_duration(self, agents: Dict[str, Any], agent_type: str = "drawdocs") -> float:
        """Calculate total duration from agent elapsed times."""
        agents_list = AGENT_TYPE_SUB_AGENTS.get(agent_type, self.AGENTS)
        total = 0.0
        for name in agents_list:
            elapsed = agents.get(name, {}).get("elapsed_seconds", 0) or 0
            total += float(elapsed)
        return round(total, 2)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global instance for convenience (uses default output directory)
# Note: This is not thread-safe, but that's fine for our use case where
# each orchestrator process runs in its own subprocess with a single thread.
# If multi-threading is needed in the future, use threading.Lock or 
# pass explicit StatusWriter instances instead.
_default_writer: Optional[StatusWriter] = None


def get_status_writer(output_dir: Optional[str] = None) -> StatusWriter:
    """
    Get a StatusWriter instance.
    
    Args:
        output_dir: Optional output directory. If None, uses default.
        
    Returns:
        StatusWriter instance
    """
    global _default_writer
    
    if output_dir:
        return StatusWriter(output_dir)
    
    if _default_writer is None:
        _default_writer = StatusWriter()
    
    return _default_writer


def initialize_run(
    loan_id: str,
    demo_mode: bool = True,
    document_types: Optional[list] = None,
    max_retries: int = 2,
    output_dir: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    """
    Convenience function to initialize a new run.
    
    Args:
        loan_id: Encompass loan GUID
        demo_mode: Demo mode flag
        document_types: Optional document types list
        max_retries: Max retry attempts
        output_dir: Optional output directory
        
    Returns:
        Tuple of (run_id, initial_data)
    """
    writer = get_status_writer(output_dir)
    run_id = writer.generate_run_id(loan_id)
    initial_data = writer.initialize_run(
        run_id=run_id,
        loan_id=loan_id,
        demo_mode=demo_mode,
        document_types=document_types,
        max_retries=max_retries,
    )
    return run_id, initial_data


# =============================================================================
# ORCHESTRATOR INTEGRATION
# =============================================================================

def create_progress_callback(run_id: str, output_dir: Optional[str] = None):
    """
    Create a progress callback function for the orchestrator.
    
    This callback is called after each agent completes and updates the status file.
    
    Args:
        run_id: The run ID for this execution
        output_dir: Optional output directory
        
    Returns:
        Callback function with signature: callback(agent_name, result, orchestrator)
    """
    writer = get_status_writer(output_dir)
    
    def progress_callback(agent_name: str, result: dict, orchestrator):
        """Update status file after agent completes."""
        status = result.get("status", "failed")
        attempts = result.get("attempts", 1)
        elapsed = result.get("elapsed_seconds", 0)
        output = result.get("output")
        error = result.get("error")
        
        if status == "success":
            writer.mark_agent_success(
                run_id=run_id,
                agent_name=agent_name,
                attempts=attempts,
                elapsed_seconds=elapsed,
                output=output,
            )
        else:
            writer.mark_agent_failed(
                run_id=run_id,
                agent_name=agent_name,
                attempts=attempts,
                elapsed_seconds=elapsed,
                error=error or "Unknown error",
            )
    
    return progress_callback


if __name__ == "__main__":
    """Test the status writer."""
    import tempfile
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = StatusWriter(tmpdir)
        
        # Test run
        test_loan_id = "test-loan-12345"
        run_id = writer.generate_run_id(test_loan_id)
        
        print(f"Generated run_id: {run_id}")
        
        # Initialize
        data = writer.initialize_run(run_id, test_loan_id, demo_mode=True)
        print(f"\nInitial data:")
        print(json.dumps(data, indent=2))
        
        # Update preparation
        data = writer.mark_agent_success(
            run_id=run_id,
            agent_name="preparation",
            attempts=1,
            elapsed_seconds=35.5,
            output={"documents_processed": 5},
        )
        print(f"\nAfter preparation success:")
        print(json.dumps(data["agents"], indent=2))
        
        # Update verification
        data = writer.mark_agent_success(
            run_id=run_id,
            agent_name="verification",
            attempts=1,
            elapsed_seconds=18.2,
            output={"corrections": 3},
        )
        print(f"\nAfter verification success:")
        print(json.dumps(data["agents"], indent=2))
        
        # Finalize
        data = writer.finalize_run(run_id, summary={"total_corrections": 3})
        print(f"\nFinal data:")
        print(json.dumps(data, indent=2))