"""
Orchestrator Agent - Manages execution of Preparation, Verification, and Orderdocs agents.

This orchestrator coordinates the sequential execution of three sub-agents:
1. Preparation Agent: Extracts field values from loan documents
2. Verification Agent: Verifies extracted values against Encompass, corrects mismatches
3. Orderdocs Agent: Checks all required fields are present (with corrections overlaid in demo mode)

Features:
- Automatic demo mode (DRY_RUN environment variable)
- Retry logic with exponential backoff
- Comprehensive reporting (JSON + human-readable summary)
- Flexible user prompt interpretation
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add agent directories to path (for their internal imports)
sys.path.insert(0, str(project_root / "agents" / "preparation_agent"))
sys.path.insert(0, str(project_root / "agents" / "verification_agent"))
sys.path.insert(0, str(project_root / "agents" / "orderdocs_agent"))

# Import sub-agents
from agents.preparation_agent.preparation_agent import process_loan_documents
from agents.verification_agent.verification_agent import run_verification
from agents.orderdocs_agent.orderdocs_agent import process_orderdocs_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator execution."""
    loan_id: str
    user_prompt: Optional[str] = None
    demo_mode: bool = True  # Always True for demo by default
    max_retries: int = 2
    document_types: Optional[List[str]] = None
    output_file: Optional[str] = None


# =============================================================================
# ORCHESTRATOR AGENT
# =============================================================================

class OrchestratorAgent:
    """Orchestrator that manages sequential execution of sub-agents."""
    
    def __init__(self, config: OrchestratorConfig, progress_callback=None):
        """Initialize orchestrator with configuration.
        
        Args:
            config: OrchestratorConfig instance
            progress_callback: Optional callback function called after each agent completes.
                              Signature: callback(agent_name: str, result: dict, orchestrator: OrchestratorAgent)
        """
        self.config = config
        self.progress_callback = progress_callback
        self.results = {
            "loan_id": config.loan_id,
            "execution_timestamp": datetime.now().isoformat(),
            "demo_mode": config.demo_mode,
            "agents": {}
        }
        
        # Parse user prompt if provided
        self.instructions = self._parse_user_prompt(config.user_prompt)
        
        # Set demo mode
        self._set_demo_mode()
    
    def _set_demo_mode(self):
        """Set DRY_RUN environment variable for demo mode."""
        if self.config.demo_mode:
            os.environ["DRY_RUN"] = "true"
            logger.info("=" * 80)
            logger.info("🔍 DEMO MODE ENABLED - No changes will be written to Encompass")
            logger.info("=" * 80)
        else:
            os.environ["DRY_RUN"] = "false"
            logger.warning("=" * 80)
            logger.warning("⚠️  PRODUCTION MODE - Changes WILL be written to Encompass")
            logger.warning("=" * 80)
    
    def _parse_user_prompt(self, prompt: Optional[str]) -> Dict[str, Any]:
        """Parse user prompt to determine execution instructions.
        
        Args:
            prompt: Optional user prompt
            
        Returns:
            Dictionary with parsed instructions
        """
        if not prompt:
            return {"run_all": True, "output_format": "both"}
        
        instructions = {
            "run_all": True,
            "skip_agents": [],
            "focus_fields": [],
            "output_format": "both",
            "additional_context": prompt
        }
        
        prompt_lower = prompt.lower()
        
        # Agent selection keywords
        if "only prep" in prompt_lower:
            instructions["skip_agents"] = ["verification", "orderdocs"]
        elif "skip verification" in prompt_lower:
            instructions["skip_agents"] = ["verification"]
        elif "skip orderdocs" in prompt_lower:
            instructions["skip_agents"] = ["orderdocs"]
        
        # Output format keywords
        if "summary only" in prompt_lower:
            instructions["output_format"] = "summary"
        elif "json only" in prompt_lower:
            instructions["output_format"] = "json"
        
        return instructions
    
    def _run_with_retry(
        self,
        agent_func,
        agent_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Run agent function with retry logic.
        
        Args:
            agent_func: Function to execute
            agent_name: Name of agent for logging
            **kwargs: Arguments to pass to agent function
            
        Returns:
            Dictionary with status and output or error
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"[{agent_name.upper()}] Attempt {attempt + 1}/{self.config.max_retries + 1}")
                
                start_time = time.time()
                result = agent_func(**kwargs)
                elapsed = time.time() - start_time
                
                logger.info(f"[{agent_name.upper()}] ✓ Success ({elapsed:.1f}s)")
                
                return {
                    "status": "success",
                    "output": result,
                    "attempts": attempt + 1,
                    "elapsed_seconds": round(elapsed, 2)
                }
            
            except Exception as e:
                logger.error(f"[{agent_name.upper()}] ✗ Attempt {attempt + 1} failed: {e}")
                
                if attempt == self.config.max_retries:
                    # Final attempt failed
                    return {
                        "status": "failed",
                        "error": str(e),
                        "attempts": attempt + 1
                    }
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                logger.info(f"[{agent_name.upper()}] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        # Should not reach here
        return {
            "status": "failed",
            "error": "Max retries exceeded",
            "attempts": self.config.max_retries + 1
        }
    
    def _run_preparation_agent(self) -> Dict[str, Any]:
        """Execute preparation agent.
        
        Returns:
            Preparation agent output
        """
        logger.info(f"[PREPARATION] Starting for loan {self.config.loan_id}")
        
        # process_loan_documents is a LangChain tool, use .invoke()
        result = process_loan_documents.invoke({
            "loan_id": self.config.loan_id,
            "document_types": self.config.document_types,
            "dry_run": True  # Prep agent doesn't write, so always dry_run
        })
        
        return result
    
    def _run_verification_agent(self, prep_output: Dict[str, Any]) -> Dict[str, Any]:
        """Execute verification agent.
        
        Args:
            prep_output: Output from preparation agent
            
        Returns:
            Verification agent output
        """
        logger.info(f"[VERIFICATION] Starting with prep output")
        
        # Extract prep output from wrapper if needed
        if "output" in prep_output:
            prep_data = prep_output["output"]
        else:
            prep_data = prep_output
        
        result = run_verification(
            loan_id=self.config.loan_id,
            prep_output=prep_data,
            dry_run=self.config.demo_mode
        )
        
        return result
    
    def _run_orderdocs_agent(
        self,
        prep_output: Dict[str, Any],
        verification_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute orderdocs agent.
        
        In demo mode, overlays verification corrections to simulate post-correction state.
        
        Args:
            prep_output: Output from preparation agent
            verification_output: Output from verification agent
            
        Returns:
            Orderdocs agent output (with corrections overlaid in demo mode)
        """
        logger.info(f"[ORDERDOCS] Starting")
        
        # Extract document types from prep output
        document_types = self._extract_document_types(prep_output)
        
        # Run orderdocs to get current Encompass values
        orderdocs_input = {
            "loan_id": self.config.loan_id,
            "document_types": document_types
        }
        
        orderdocs_result = process_orderdocs_request(orderdocs_input)
        
        # In demo mode: overlay verification corrections
        if self.config.demo_mode:
            corrections = self._extract_corrections(verification_output)
            if corrections:
                logger.info(f"[ORDERDOCS] Applying {len(corrections)} corrections from verification")
                orderdocs_result = self._apply_demo_corrections(
                    orderdocs_result,
                    corrections
                )
        
        return orderdocs_result
    
    def _extract_document_types(self, prep_output: Dict[str, Any]) -> List[str]:
        """Extract document types from prep output.
        
        Args:
            prep_output: Preparation agent output
            
        Returns:
            List of document types processed
        """
        # Extract from wrapper if needed
        if "output" in prep_output:
            prep_data = prep_output["output"]
        else:
            prep_data = prep_output
        
        # Get document types from extracted_entities
        extracted_entities = prep_data.get("results", {}).get("extracted_entities", {})
        doc_types = list(extracted_entities.keys())
        
        if not doc_types:
            # Fallback: use common document types
            doc_types = ["ID", "Title Report", "LE", "1003", "Appraisal"]
        
        return doc_types
    
    def _extract_corrections(self, verification_output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract corrections from verification agent output.
        
        Args:
            verification_output: Verification agent output
            
        Returns:
            Dictionary mapping field_id -> {value, source_document}
        """
        corrections = {}
        
        # Handle nested structure
        if "output" in verification_output:
            ver_data = verification_output["output"]
        else:
            ver_data = verification_output
        
        # Look for corrections in messages
        messages = ver_data.get("messages", [])
        
        for msg in messages:
            msg_type = type(msg).__name__
            
            if msg_type == "ToolMessage":
                content = getattr(msg, 'content', '')
                
                # Try to parse JSON string content
                if isinstance(content, str) and content.startswith('{'):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                
                # Check if content is a correction record
                if isinstance(content, dict):
                    if "field_id" in content and "corrected_value" in content:
                        if content.get("success"):
                            corrections[content["field_id"]] = {
                                "value": content["corrected_value"],
                                "source_document": content.get("source_document"),
                                "field_name": content.get("field_name", content["field_id"])
                            }
        
        return corrections
    
    def _apply_demo_corrections(
        self,
        orderdocs_result: Dict[str, Any],
        corrections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Overlay verification corrections onto orderdocs result.
        
        Simulates what Encompass would look like if corrections were written.
        
        Args:
            orderdocs_result: Original orderdocs output
            corrections: Dictionary of field_id -> {value, source_document, field_name}
            
        Returns:
            Updated orderdocs result with corrections applied
        """
        for field_id, correction_data in corrections.items():
            corrected_value = correction_data["value"]
            
            if field_id in orderdocs_result:
                # Update existing field
                orderdocs_result[field_id]["value"] = corrected_value
                orderdocs_result[field_id]["correction_applied"] = True
                orderdocs_result[field_id]["has_value"] = True
            else:
                # Add missing field
                orderdocs_result[field_id] = {
                    "value": corrected_value,
                    "has_value": True,
                    "correction_applied": True
                }
        
        return orderdocs_result
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """Aggregate results from all agents into structured JSON.
        
        Returns:
            Aggregated results dictionary
        """
        aggregated = {
            "loan_id": self.config.loan_id,
            "execution_timestamp": self.results["execution_timestamp"],
            "demo_mode": self.config.demo_mode,
            "summary": self.results.get("summary", {}),
            "agents": {}
        }
        
        # Add each agent's results
        for agent_name, agent_result in self.results["agents"].items():
            aggregated["agents"][agent_name] = {
                "status": agent_result.get("status"),
                "attempts": agent_result.get("attempts"),
                "elapsed_seconds": agent_result.get("elapsed_seconds"),
                "output": agent_result.get("output"),
                "error": agent_result.get("error")
            }
        
        # Add corrected fields summary with document filenames
        ver_result = self.results["agents"].get("verification", {})
        if ver_result:
            corrections = self._extract_corrections(ver_result)
            if corrections:
                corrected_fields_summary = []
                for field_id, correction_data in corrections.items():
                    attachment_id = correction_data.get("source_document")
                    document_filename = f"{attachment_id}.pdf" if attachment_id else "Unknown"
                    
                    corrected_fields_summary.append({
                        "field_id": field_id,
                        "field_name": correction_data.get("field_name", field_id),
                        "corrected_value": correction_data["value"],
                        "source_document": attachment_id,
                        "document_filename": document_filename
                    })
                
                aggregated["corrected_fields_summary"] = corrected_fields_summary
        
        return aggregated
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary of execution.
        
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ORCHESTRATOR EXECUTION SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Loan ID: {self.config.loan_id}")
        lines.append(f"Timestamp: {self.results['execution_timestamp']}")
        lines.append(f"Mode: {'DEMO (no actual writes)' if self.config.demo_mode else 'PRODUCTION'}")
        lines.append("")
        
        # Preparation Agent
        prep_result = self.results["agents"].get("preparation", {})
        if prep_result:
            status = prep_result.get("status", "unknown")
            symbol = "✓" if status == "success" else "✗"
            lines.append(f"[PREPARATION AGENT]")
            lines.append(f"{symbol} {status.title()} ({prep_result.get('attempts', 0)} attempt(s))")
            
            if status == "success":
                prep_output = prep_result.get("output", {})
                docs_processed = prep_output.get("documents_processed", 0)
                total_docs = prep_output.get("total_documents_found", 0)
                fields = len(prep_output.get("results", {}).get("field_mappings", {}))
                lines.append(f"- Documents processed: {docs_processed}/{total_docs}")
                lines.append(f"- Fields extracted: {fields}")
            elif status == "failed":
                lines.append(f"- Error: {prep_result.get('error', 'Unknown')}")
            lines.append("")
        
        # Verification Agent
        ver_result = self.results["agents"].get("verification", {})
        if ver_result:
            status = ver_result.get("status", "unknown")
            symbol = "✓" if status == "success" else "✗"
            lines.append(f"[VERIFICATION AGENT]")
            lines.append(f"{symbol} {status.title()} ({ver_result.get('attempts', 0)} attempt(s))")
            
            if status == "success":
                # Extract corrections
                corrections = self._extract_corrections(ver_result)
                lines.append(f"- Corrections needed: {len(corrections)}")
                
                # Show first few corrections with document filenames
                for i, (field_id, correction_data) in enumerate(list(corrections.items())[:5]):
                    value = correction_data["value"]
                    attachment_id = correction_data.get("source_document")
                    doc_filename = f"{attachment_id}.pdf" if attachment_id else "Unknown"
                    field_name = correction_data.get("field_name", field_id)
                    
                    # Truncate long values
                    value_str = str(value)
                    if len(value_str) > 40:
                        value_str = value_str[:37] + "..."
                    
                    lines.append(f"  • Field {field_id} ({field_name}): '{value_str}'")
                    lines.append(f"    Source: {doc_filename}")
                
                if len(corrections) > 5:
                    lines.append(f"  ... and {len(corrections) - 5} more")
            elif status == "failed":
                lines.append(f"- Error: {ver_result.get('error', 'Unknown')}")
            lines.append("")
        
        # Orderdocs Agent
        ord_result = self.results["agents"].get("orderdocs", {})
        if ord_result:
            status = ord_result.get("status", "unknown")
            symbol = "✓" if status == "success" else "✗"
            lines.append(f"[ORDERDOCS AGENT]")
            lines.append(f"{symbol} {status.title()} ({ord_result.get('attempts', 0)} attempt(s))")
            
            if status == "success":
                ord_output = ord_result.get("output", {})
                total_fields = len(ord_output)
                fields_with_value = sum(1 for f in ord_output.values() if isinstance(f, dict) and f.get("has_value"))
                corrected = sum(1 for f in ord_output.values() if isinstance(f, dict) and f.get("correction_applied"))
                
                lines.append(f"- Total fields checked: {total_fields}")
                lines.append(f"- Fields with values: {fields_with_value}")
                if corrected > 0:
                    lines.append(f"- Corrections applied (demo): {corrected}")
            elif status == "failed":
                lines.append(f"- Error: {ord_result.get('error', 'Unknown')}")
            lines.append("")
        
        # Overall status
        all_success = all(
            r.get("status") == "success"
            for r in self.results["agents"].values()
        )
        lines.append(f"OVERALL STATUS: {'SUCCESS' if all_success else 'PARTIAL FAILURE'}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def run(self) -> Dict[str, Any]:
        """Execute orchestrator workflow.
        
        Runs agents sequentially with retry logic.
        
        Returns:
            Complete results dictionary
        """
        logger.info("=" * 80)
        logger.info(f"ORCHESTRATOR STARTING - Loan {self.config.loan_id}")
        logger.info("=" * 80)
        
        # Step 1: Preparation Agent
        if "preparation" not in self.instructions.get("skip_agents", []):
            prep_result = self._run_with_retry(
                self._run_preparation_agent,
                "preparation"
            )
            self.results["agents"]["preparation"] = prep_result
            
            # Call progress callback
            if self.progress_callback:
                self.progress_callback("preparation", prep_result, self)
            
            if prep_result["status"] != "success":
                logger.error("[PREPARATION] Failed - stopping orchestration")
                self.results["summary_text"] = self._generate_summary()
                return self.results
        else:
            logger.info("[PREPARATION] Skipped per user request")
        
        # Step 2: Verification Agent
        if "verification" not in self.instructions.get("skip_agents", []):
            if "preparation" in self.results["agents"]:
                ver_result = self._run_with_retry(
                    self._run_verification_agent,
                    "verification",
                    prep_output=self.results["agents"]["preparation"]
                )
                self.results["agents"]["verification"] = ver_result
                
                # Call progress callback
                if self.progress_callback:
                    self.progress_callback("verification", ver_result, self)
                
                if ver_result["status"] != "success":
                    logger.error("[VERIFICATION] Failed - continuing to orderdocs")
            else:
                logger.warning("[VERIFICATION] Skipped - no preparation output")
        else:
            logger.info("[VERIFICATION] Skipped per user request")
        
        # Step 3: Orderdocs Agent
        if "orderdocs" not in self.instructions.get("skip_agents", []):
            if "preparation" in self.results["agents"]:
                ord_result = self._run_with_retry(
                    self._run_orderdocs_agent,
                    "orderdocs",
                    prep_output=self.results["agents"]["preparation"],
                    verification_output=self.results["agents"].get("verification", {})
                )
                self.results["agents"]["orderdocs"] = ord_result
                
                # Call progress callback
                if self.progress_callback:
                    self.progress_callback("orderdocs", ord_result, self)
            else:
                logger.warning("[ORDERDOCS] Skipped - no preparation output")
        else:
            logger.info("[ORDERDOCS] Skipped per user request")
        
        # Generate summary
        self.results["summary_text"] = self._generate_summary()
        self.results["json_output"] = self._aggregate_results()
        
        logger.info("=" * 80)
        logger.info("ORCHESTRATOR COMPLETED")
        logger.info("=" * 80)
        
        return self.results


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_orchestrator(
    loan_id: str,
    user_prompt: Optional[str] = None,
    demo_mode: bool = True,
    max_retries: int = 2,
    document_types: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    progress_callback=None
) -> Dict[str, Any]:
    """Run the orchestrator agent.
    
    Main entry point for orchestrating all sub-agents.
    
    Args:
        loan_id: Encompass loan GUID
        user_prompt: Optional user prompt for custom instructions
        demo_mode: If True, run in demo mode (no actual writes). Default: True
        max_retries: Maximum retry attempts per agent. Default: 2
        document_types: Optional list of document types to process
        output_file: Optional file path to save results
        progress_callback: Optional callback function called after each agent completes.
                          Signature: callback(agent_name: str, result: dict, orchestrator: OrchestratorAgent)
        
    Returns:
        Dictionary with complete execution results
        
    Example:
        >>> results = run_orchestrator(
        ...     loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
        ...     demo_mode=True
        ... )
        >>> print(results["summary_text"])
    """
    config = OrchestratorConfig(
        loan_id=loan_id,
        user_prompt=user_prompt,
        demo_mode=demo_mode,
        max_retries=max_retries,
        document_types=document_types,
        output_file=output_file
    )
    
    orchestrator = OrchestratorAgent(config, progress_callback=progress_callback)
    results = orchestrator.run()
    
    # Print summary
    print("\n" + results["summary_text"])
    
    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        
        # Save JSON output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results["json_output"], f, indent=2, default=str)
        
        logger.info(f"Results saved to: {output_path}")
        
        # Also save summary text
        summary_file = output_path.parent / f"{output_path.stem}_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(results["summary_text"])
        
        logger.info(f"Summary saved to: {summary_file}")
    
    return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Orchestrator Agent - Manages Preparation, Verification, and Orderdocs agents"
    )
    parser.add_argument(
        "--loan-id",
        required=True,
        help="Encompass loan GUID"
    )
    parser.add_argument(
        "--prompt",
        help="Optional user prompt for custom instructions"
    )
    parser.add_argument(
        "--output",
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
    
    args = parser.parse_args()
    
    # Run orchestrator
    results = run_orchestrator(
        loan_id=args.loan_id,
        user_prompt=args.prompt,
        demo_mode=not args.production,
        max_retries=args.max_retries,
        output_file=args.output
    )
    
    # Exit with appropriate code
    all_success = all(
        r.get("status") == "success"
        for r in results["agents"].values()
    )
    sys.exit(0 if all_success else 1)

