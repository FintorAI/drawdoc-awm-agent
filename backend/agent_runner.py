"""
Multi-Agent Runner Script

This script runs agent orchestrators (DrawDocs, Disclosure, LOA) and updates 
the status JSON file after each sub-agent completes, enabling live status updates.

Usage:
    python agent_runner.py --loan-id <uuid> --agent-type <type> --output <path> [--production] [--max-retries N] [--document-types type1,type2]

Supported agent types:
- drawdocs: Document extraction → Field writing → Verification → Order closing docs
- disclosure: TRID verification → LE preparation → Mavent/ATR-QM → Order disclosures  
- loa: (future) Letter of Authorization processing

The status file is updated in real-time using the StatusWriter utility,
allowing the frontend to poll for live progress updates.

Status transitions:
- "pending" → "running" (when agent starts)
- "running" → "success" (when agent completes successfully)
- "running" → "failed" (when agent errors after all retries)
- "running" → "blocked" (disclosure: compliance block)
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import status writer
from agents.drawdocs.status_writer import StatusWriter, get_status_writer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def _add_agent_summary_logs(writer: StatusWriter, run_id: str, agent_name: str, output: dict) -> None:
    """
    Add summary logs based on agent output.
    
    Extracts key information from each agent's output and logs it.
    """
    if not output:
        return
    
    try:
        if agent_name == "preparation":
            # Log document processing summary
            docs_found = output.get("total_documents_found", 0)
            docs_processed = output.get("documents_processed", 0)
            
            writer.add_log(
                run_id=run_id,
                message=f"Processed {docs_processed} of {docs_found} documents",
                level="info",
                agent="preparation",
                event_type="prep_summary",
                details={"documents_found": docs_found, "documents_processed": docs_processed},
            )
            
            # Log field mappings count
            results = output.get("results", {})
            field_mappings = results.get("field_mappings", {})
            if field_mappings:
                writer.add_log(
                    run_id=run_id,
                    message=f"Mapped {len(field_mappings)} fields to Encompass IDs",
                    level="info",
                    agent="preparation",
                    event_type="field_mappings",
                    details={"field_count": len(field_mappings)},
                )
                
        elif agent_name == "drawcore":
            # Log drawcore summary
            phases_completed = output.get("phases_completed", 0)
            total_phases = output.get("total_phases", 5)
            fields_updated = output.get("fields_updated", 0)
            fields_failed = output.get("fields_failed", 0)
            
            writer.log_drawcore_summary(
                run_id=run_id,
                phases_completed=phases_completed,
                total_phases=total_phases,
                fields_updated=fields_updated,
                fields_failed=fields_failed,
            )
                
        elif agent_name == "verification":
            # Log corrections summary
            corrections = output.get("corrections", [])
            if corrections:
                writer.log_verification_summary(
                    run_id=run_id,
                    corrections_count=len(corrections),
                    fields_checked=output.get("fields_checked", len(corrections)),
                )
                
                # Log first few corrections as examples
                for correction in corrections[:3]:
                    field_id = correction.get("field_id", "")
                    field_name = correction.get("field_name", field_id)
                    new_value = correction.get("corrected_value", "")
                    reason = correction.get("reason", "")
                    
                    writer.log_field_correction(
                        run_id=run_id,
                        field_id=field_id,
                        field_name=field_name,
                        old_value="",  # We don't always have the old value
                        new_value=new_value,
                        reason=reason,
                    )
                    
        elif agent_name == "orderdocs":
            # Log orderdocs summary
            total_fields = len(output) if isinstance(output, dict) else 0
            fields_with_values = sum(
                1 for v in output.values() 
                if isinstance(v, dict) and v.get("has_value")
            ) if isinstance(output, dict) else 0
            
            corrections_applied = output.get("corrections_applied", 0) if isinstance(output, dict) else 0
            
            writer.log_orderdocs_summary(
                run_id=run_id,
                total_fields=total_fields,
                fields_with_values=fields_with_values,
                corrections_applied=corrections_applied,
            )
            
    except Exception as e:
        logger.warning(f"Failed to add summary logs for {agent_name}: {e}")


def create_status_callback(run_id: str, output_dir: Path):
    """
    Create a progress callback that updates the status file using StatusWriter.
    
    Args:
        run_id: The run identifier
        output_dir: Directory containing the status file
        
    Returns:
        Callback function for orchestrator progress updates
    """
    writer = StatusWriter(output_dir)
    agents_started = set()  # Track which agents have had start logged
    
    def progress_callback(agent_name: str, result: dict, orchestrator) -> None:
        """
        Progress callback that updates the status file after each agent completes.
        
        Uses StatusWriter for clean status transitions:
        - "running" → "success" (if agent succeeded)
        - "running" → "failed" (if agent failed)
        - Next agent is set to "running" automatically on success
        
        Args:
            agent_name: Name of the agent that completed
            result: Result from the agent
            orchestrator: The OrchestratorAgent instance
        """
        try:
            status = result.get("status", "failed")
            attempts = result.get("attempts", 1)
            elapsed = result.get("elapsed_seconds", 0)
            output = result.get("output")
            error = result.get("error")
            
            if status == "success":
                # Mark agent as success - StatusWriter will set next agent to "running"
                writer.mark_agent_success(
                    run_id=run_id,
                    agent_name=agent_name,
                    attempts=attempts,
                    elapsed_seconds=elapsed,
                    output=output,
                )
                # Add structured success log
                writer.log_agent_complete(
                    run_id=run_id,
                    agent_name=agent_name,
                    elapsed_seconds=elapsed,
                    success=True,
                )
                
                # Add agent-specific summary logs
                _add_agent_summary_logs(writer, run_id, agent_name, output)
                
                logger.info(f"Updated status file: {agent_name} → success")
            else:
                # Mark agent as failed
                writer.mark_agent_failed(
                    run_id=run_id,
                    agent_name=agent_name,
                    attempts=attempts,
                    elapsed_seconds=elapsed,
                    error=error or "Unknown error",
                )
                # Add structured failure log
                writer.log_agent_complete(
                    run_id=run_id,
                    agent_name=agent_name,
                    elapsed_seconds=elapsed,
                    success=False,
                    error=error,
                )
                logger.info(f"Updated status file: {agent_name} → failed")
                
        except Exception as e:
            logger.error(f"Failed to update status file after {agent_name}: {e}")
    
    return progress_callback


def extract_run_id_from_output_file(output_file: Path) -> str:
    """
    Extract run_id from output file path.
    
    Expected format: {run_id}_results.json
    Where run_id = {loan_id}_{timestamp}
    
    Args:
        output_file: Path to output file
        
    Returns:
        The run_id string
    """
    filename = output_file.name
    if filename.endswith("_results.json"):
        return filename[:-13]  # Remove "_results.json"
    return filename


def run_agent(
    loan_id: str,
    agent_type: str,
    output_file: Path,
    demo_mode: bool = True,
    max_retries: int = 2,
    document_types: Optional[list[str]] = None,
    lo_email: Optional[str] = None,
    require_review: bool = False,
    resume_from: Optional[str] = None,
) -> None:
    """
    Run the orchestrator agent with live status updates.
    
    The status file is updated after each agent completes using StatusWriter,
    allowing the frontend to poll for live progress updates.
    
    Args:
        loan_id: Encompass loan GUID
        agent_type: Type of agent pipeline ("drawdocs", "disclosure", "loa")
        output_file: Path to the output JSON file
        demo_mode: Whether to run in demo mode
        max_retries: Number of retry attempts per agent
        document_types: Optional list of document types to process (DrawDocs only)
        lo_email: Loan officer email (Disclosure/LOA only)
        require_review: If True, pause after prep agent for user review (HIL)
        resume_from: If set, resume run from this agent (e.g., "drawcore")
    """
    # Extract run_id and output directory
    run_id = extract_run_id_from_output_file(output_file)
    output_dir = output_file.parent
    
    # Create status writer for error handling
    writer = StatusWriter(output_dir)
    
    # Agent type to sub-agents mapping for error handling
    agent_type_sub_agents = {
        "drawdocs": ["preparation", "drawcore", "verification", "orderdocs"],
        "disclosure": ["verification", "preparation", "send"],
        "loa": ["verification", "generation", "delivery"],
    }
    
    try:
        if agent_type == "drawdocs":
            # Import DrawDocs orchestrator
            from agents.drawdocs.orchestrator_agent import run_orchestrator
            
            # Set up live progress callback for preparation agent
            from agents.drawdocs.subagents.preparation_agent.preparation_agent import set_progress_callback, set_log_callback
            
            def prep_progress_callback(documents_found=None, documents_processed=None, fields_extracted=None, current_document=None):
                """Update status file with live progress from preparation agent."""
                try:
                    writer.update_progress(
                        run_id=run_id,
                        documents_found=documents_found,
                        documents_processed=documents_processed,
                        fields_extracted=fields_extracted,
                        current_document=current_document,
                    )
                except Exception as e:
                    logger.warning(f"Failed to update progress: {e}")
            
            def prep_log_callback(message: str, level: str = "info", event_type: str = None, details: dict = None):
                """Add log entry from preparation agent."""
                try:
                    writer.add_log(
                        run_id=run_id,
                        message=message,
                        level=level,
                        agent="preparation",
                        event_type=event_type,
                        details=details,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add log: {e}")
            
            set_progress_callback(prep_progress_callback)
            set_log_callback(prep_log_callback)
            
            # Create progress callback using StatusWriter
            progress_callback = create_status_callback(run_id, output_dir)
            
            # Check if resuming from a specific agent (HIL continuation)
            if resume_from:
                logger.info(f"Resuming run from {resume_from}")
                
                # Load existing results from the status file
                existing_data = writer.get_run_data(run_id)
                existing_results = None
                if existing_data:
                    existing_results = {
                        "loan_id": existing_data.get("loan_id", loan_id),
                        "execution_timestamp": existing_data.get("execution_timestamp"),
                        "demo_mode": existing_data.get("demo_mode", demo_mode),
                        "agents": existing_data.get("agents", {}),
                    }
                    logger.info(f"Loaded existing results with {len(existing_results.get('agents', {}))} agents")
                
                # Run orchestrator starting from the specified agent
                results = run_orchestrator(
                    loan_id=loan_id,
                    demo_mode=demo_mode,
                    max_retries=max_retries,
                    document_types=document_types,
                    output_file=str(output_file),
                    progress_callback=progress_callback,
                    start_from_agent=resume_from,
                    existing_results=existing_results,
                )
            elif require_review:
                # Run only the prep agent, then pause for review (HIL)
                logger.info("Running prep agent only (HIL review enabled)")
                results = run_orchestrator(
                    loan_id=loan_id,
                    demo_mode=demo_mode,
                    max_retries=max_retries,
                    document_types=document_types,
                    output_file=str(output_file),
                    progress_callback=progress_callback,
                    stop_after_agent="preparation",
                )
                
                # Mark run as pending review instead of finalizing
                if results.get("agents", {}).get("preparation", {}).get("status") == "success":
                    writer.mark_agent_pending_review(
                        run_id=run_id,
                        agent_name="preparation",
                        attempts=results.get("agents", {}).get("preparation", {}).get("attempts", 1),
                        elapsed_seconds=results.get("agents", {}).get("preparation", {}).get("elapsed_seconds", 0),
                        output=results.get("agents", {}).get("preparation", {}).get("output"),
                    )
                    
                    # Add log entry for user
                    writer.add_log(
                        run_id=run_id,
                        message="Waiting for field review before proceeding",
                        level="info",
                        agent="preparation",
                        event_type="pending_review",
                    )
                    
                    logger.info(f"Run paused for review - waiting for user to approve fields")
                    
                    # Clear callbacks and exit early
                    set_progress_callback(None)
                    set_log_callback(None)
                    return
            else:
                # Run full orchestrator
                results = run_orchestrator(
                    loan_id=loan_id,
                    demo_mode=demo_mode,
                    max_retries=max_retries,
                    document_types=document_types,
                    output_file=str(output_file),
                    progress_callback=progress_callback,
                )
            
            # Clear callbacks
            set_progress_callback(None)
            set_log_callback(None)
            
        elif agent_type == "disclosure":
            # Import Disclosure orchestrator
            from agents.disclosure.orchestrator_agent import run_disclosure_orchestrator
            
            # Create progress callback using StatusWriter
            progress_callback = create_status_callback(run_id, output_dir)
            
            # Run Disclosure orchestrator
            results = run_disclosure_orchestrator(
                loan_id=loan_id,
                lo_email=lo_email or "",  # Default to empty string if not provided
                demo_mode=demo_mode,
                max_retries=max_retries,
                progress_callback=progress_callback,
            )
            
        elif agent_type == "loa":
            # LOA not yet implemented
            raise NotImplementedError(f"Agent type '{agent_type}' is not yet implemented")
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Finalize the run with summary information
        writer.finalize_run(
            run_id=run_id,
            summary=results.get("summary", {}),
            summary_text=results.get("summary_text") or results.get("summary"),
        )
        
        logger.info(f"{agent_type} agent run completed for loan {loan_id}")
        
    except Exception as e:
        logger.error(f"{agent_type} agent run failed: {e}")
        
        # Update status file to reflect failure using StatusWriter
        try:
            # Read current data to find which agent was running
            data = writer.get_run_data(run_id)
            sub_agents = agent_type_sub_agents.get(agent_type, agent_type_sub_agents["drawdocs"])
            
            if data:
                # Find which agent was running and mark it as failed
                for agent_name in sub_agents:
                    agent_data = data.get("agents", {}).get(agent_name, {})
                    if agent_data.get("status") == "running":
                        writer.mark_agent_failed(
                            run_id=run_id,
                            agent_name=agent_name,
                            attempts=agent_data.get("attempts", 0) + 1,
                            elapsed_seconds=agent_data.get("elapsed_seconds", 0),
                            error=str(e),
                        )
                        break
            else:
                # Status file doesn't exist - create a minimal failure record
                logger.warning(f"Status file not found for run {run_id}, creating failure record")
                first_agent = sub_agents[0] if sub_agents else "preparation"
                writer.initialize_run(run_id, loan_id, demo_mode, agent_type=agent_type)
                writer.mark_agent_failed(
                    run_id=run_id,
                    agent_name=first_agent,
                    attempts=1,
                    elapsed_seconds=0,
                    error=str(e),
                )
                
        except Exception as write_error:
            logger.error(f"Failed to write error status: {write_error}")
        
        sys.exit(1)


def main():
    """Main entry point for the agent runner."""
    parser = argparse.ArgumentParser(
        description="Run multi-agent orchestrators (DrawDocs, Disclosure, LOA) with live status updates"
    )
    parser.add_argument(
        "--loan-id",
        required=True,
        help="Encompass loan GUID"
    )
    parser.add_argument(
        "--agent-type",
        choices=["drawdocs", "disclosure", "loa"],
        default="drawdocs",
        help="Type of agent pipeline to run (default: drawdocs)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path for results (JSON)"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run in PRODUCTION mode (actually write to Encompass). Default is DEMO mode."
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts per agent (default: 2)"
    )
    parser.add_argument(
        "--document-types",
        help="Comma-separated list of document types to process (DrawDocs only)"
    )
    parser.add_argument(
        "--lo-email",
        help="Loan officer email address (required for Disclosure and LOA agents)"
    )
    parser.add_argument(
        "--require-review",
        action="store_true",
        help="Pause after prep agent for user to review fields (HIL)"
    )
    parser.add_argument(
        "--resume-from",
        choices=["drawcore", "verification", "orderdocs"],
        help="Resume run from specified agent (for continuing after HIL review)"
    )
    
    args = parser.parse_args()
    
    # Parse document types
    document_types = None
    if args.document_types:
        document_types = [dt.strip() for dt in args.document_types.split(",")]
    
    # Run the agent
    run_agent(
        loan_id=args.loan_id,
        agent_type=args.agent_type,
        output_file=Path(args.output),
        demo_mode=not args.production,
        max_retries=args.max_retries,
        document_types=document_types,
        lo_email=args.lo_email,
        require_review=args.require_review,
        resume_from=args.resume_from,
    )


if __name__ == "__main__":
    main()

