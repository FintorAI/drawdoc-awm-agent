"""
Agent Runner Script

This script runs the orchestrator agent and updates the status JSON file
after each sub-agent completes, enabling live status updates.

Usage:
    python agent_runner.py --loan-id <uuid> --output <path> [--production] [--max-retries N] [--document-types type1,type2]
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def update_status_file(
    output_file: Path,
    agent_name: str,
    result: dict,
    orchestrator
) -> None:
    """
    Progress callback that updates the status file after each agent completes.
    
    Args:
        agent_name: Name of the agent that completed
        result: Result from the agent
        orchestrator: The OrchestratorAgent instance
    """
    try:
        # Build current state from orchestrator
        current_data = {
            "loan_id": orchestrator.config.loan_id,
            "execution_timestamp": orchestrator.results.get("execution_timestamp"),
            "demo_mode": orchestrator.config.demo_mode,
            "summary": orchestrator.results.get("summary", {}),
            "agents": {}
        }
        
        # Add all agent results
        for name in ["preparation", "verification", "orderdocs"]:
            agent_result = orchestrator.results.get("agents", {}).get(name)
            if agent_result:
                current_data["agents"][name] = {
                    "status": agent_result.get("status", "pending"),
                    "attempts": agent_result.get("attempts", 0),
                    "elapsed_seconds": agent_result.get("elapsed_seconds", 0),
                    "output": agent_result.get("output"),
                    "error": agent_result.get("error"),
                }
            else:
                # Agent hasn't run yet - determine status
                if name == "preparation":
                    # If we're past preparation, it should have a result
                    status = "pending"
                elif name == "verification":
                    # Running if preparation is done and we haven't gotten to verification yet
                    prep_result = orchestrator.results.get("agents", {}).get("preparation")
                    if prep_result and prep_result.get("status") == "success":
                        if agent_name == "preparation":
                            status = "running"
                        else:
                            status = "pending"
                    else:
                        status = "pending"
                else:  # orderdocs
                    ver_result = orchestrator.results.get("agents", {}).get("verification")
                    if ver_result:
                        if agent_name == "verification":
                            status = "running"
                        else:
                            status = "pending"
                    else:
                        status = "pending"
                
                current_data["agents"][name] = {
                    "status": status,
                    "attempts": 0,
                    "elapsed_seconds": 0,
                    "output": None,
                    "error": None,
                }
        
        # Update status for next agent to "running"
        if agent_name == "preparation" and result.get("status") == "success":
            if "verification" not in orchestrator.instructions.get("skip_agents", []):
                current_data["agents"]["verification"]["status"] = "running"
        elif agent_name == "verification":
            if "orderdocs" not in orchestrator.instructions.get("skip_agents", []):
                current_data["agents"]["orderdocs"]["status"] = "running"
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2, default=str)
        
        logger.info(f"Updated status file after {agent_name} completed")
        
    except Exception as e:
        logger.error(f"Failed to update status file: {e}")


def run_agent(
    loan_id: str,
    output_file: Path,
    demo_mode: bool = True,
    max_retries: int = 2,
    document_types: Optional[list[str]] = None,
) -> None:
    """
    Run the orchestrator agent with live status updates.
    
    Args:
        loan_id: Encompass loan GUID
        output_file: Path to the output JSON file
        demo_mode: Whether to run in demo mode
        max_retries: Number of retry attempts per agent
        document_types: Optional list of document types to process
    """
    try:
        # Import orchestrator (after path setup)
        from agents.drawdocs.orchestrator_agent import run_orchestrator
        
        # Create progress callback that captures output_file
        def progress_callback(agent_name: str, result: dict, orchestrator):
            update_status_file(output_file, agent_name, result, orchestrator)
        
        # Run orchestrator with progress callback
        results = run_orchestrator(
            loan_id=loan_id,
            demo_mode=demo_mode,
            max_retries=max_retries,
            document_types=document_types,
            output_file=str(output_file),
            progress_callback=progress_callback,
        )
        
        logger.info(f"Agent run completed for loan {loan_id}")
        
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        
        # Update status file to reflect failure
        try:
            # Load current data
            if output_file.exists():
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "loan_id": loan_id,
                    "execution_timestamp": datetime.now().isoformat(),
                    "demo_mode": demo_mode,
                    "summary": {},
                    "agents": {},
                }
            
            # Find which agent failed and update
            for agent_name in ["preparation", "verification", "orderdocs"]:
                agent_data = data.get("agents", {}).get(agent_name, {})
                if agent_data.get("status") == "running":
                    data["agents"][agent_name] = {
                        "status": "failed",
                        "attempts": agent_data.get("attempts", 0) + 1,
                        "elapsed_seconds": agent_data.get("elapsed_seconds", 0),
                        "output": None,
                        "error": str(e),
                    }
                    break
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                
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

