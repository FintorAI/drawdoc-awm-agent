"""
Agent Runner Script

This script runs the orchestrator agent and updates the status JSON file
after each sub-agent completes, enabling live status updates.

Usage:
    python agent_runner.py --loan-id <uuid> --output <path> [--production] [--max-retries N] [--document-types type1,type2]

The status file is updated in real-time using the StatusWriter utility,
allowing the frontend to poll for live progress updates.

Status transitions:
- "pending" → "running" (when agent starts)
- "running" → "success" (when agent completes successfully)
- "running" → "failed" (when agent errors after all retries)
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
    output_file: Path,
    demo_mode: bool = True,
    max_retries: int = 2,
    document_types: Optional[list[str]] = None,
) -> None:
    """
    Run the orchestrator agent with live status updates.
    
    The status file is updated after each agent completes using StatusWriter,
    allowing the frontend to poll for live progress updates.
    
    Args:
        loan_id: Encompass loan GUID
        output_file: Path to the output JSON file
        demo_mode: Whether to run in demo mode
        max_retries: Number of retry attempts per agent
        document_types: Optional list of document types to process
    """
    # Extract run_id and output directory
    run_id = extract_run_id_from_output_file(output_file)
    output_dir = output_file.parent
    
    # Create status writer for error handling
    writer = StatusWriter(output_dir)
    
    try:
        # Import orchestrator (after path setup)
        from agents.drawdocs.orchestrator_agent import run_orchestrator
        
        # Create progress callback using StatusWriter
        progress_callback = create_status_callback(run_id, output_dir)
        
        # Run orchestrator with progress callback
        results = run_orchestrator(
            loan_id=loan_id,
            demo_mode=demo_mode,
            max_retries=max_retries,
            document_types=document_types,
            output_file=str(output_file),
            progress_callback=progress_callback,
        )
        
        # Finalize the run with summary information
        # Note: Don't include json_output as it would duplicate data already 
        # maintained by StatusWriter callbacks
        writer.finalize_run(
            run_id=run_id,
            summary=results.get("summary", {}),
            summary_text=results.get("summary_text"),
        )
        
        logger.info(f"Agent run completed for loan {loan_id}")
        
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        
        # Update status file to reflect failure using StatusWriter
        try:
            # Read current data to find which agent was running
            data = writer.get_run_data(run_id)
            
            if data:
                # Find which agent was running and mark it as failed
                for agent_name in ["preparation", "verification", "orderdocs"]:
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
                writer.initialize_run(run_id, loan_id, demo_mode)
                writer.mark_agent_failed(
                    run_id=run_id,
                    agent_name="preparation",
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
        description="Run the DrawDoc agent orchestrator with live status updates"
    )
    parser.add_argument(
        "--loan-id",
        required=True,
        help="Encompass loan GUID"
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
        help="Comma-separated list of document types to process"
    )
    
    args = parser.parse_args()
    
    # Parse document types
    document_types = None
    if args.document_types:
        document_types = [dt.strip() for dt in args.document_types.split(",")]
    
    # Run the agent
    run_agent(
        loan_id=args.loan_id,
        output_file=Path(args.output),
        demo_mode=not args.production,
        max_retries=args.max_retries,
        document_types=document_types,
    )


if __name__ == "__main__":
    main()

