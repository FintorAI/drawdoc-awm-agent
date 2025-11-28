"""Disclosure Orchestrator Agent.

MVP: Manages sequential execution of disclosure sub-agents with non-MVP case handling.

Workflow:
1. Verification: Check required fields + MVP eligibility
2. Preparation: Calculate MI, check tolerance, populate CD
3. Request: Send email to LO with full summary
4. Handoff: Generate handoff data for Draw Docs
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import sub-agents
from agents.disclosure.subagents.verification_agent.verification_agent import run_disclosure_verification
from agents.disclosure.subagents.preparation_agent.preparation_agent import run_disclosure_preparation
from agents.disclosure.subagents.request_agent.request_agent import run_disclosure_request

# Import shared utilities
from packages.shared import (
    get_loan_type,
    LoanType,
    PropertyState,
    DisclosureHandoff,
    create_handoff_from_results,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class DisclosureConfig:
    """Configuration for disclosure orchestrator."""
    loan_id: str
    lo_email: str
    demo_mode: bool = True
    max_retries: int = 2
    skip_non_mvp: bool = False  # If True, skip processing for non-MVP loans


class DisclosureOrchestrator:
    """Orchestrator for disclosure agent pipeline.
    
    MVP workflow:
    1. Verify fields + check MVP eligibility
    2. If non-MVP and skip_non_mvp=True, return early with manual_required status
    3. Calculate MI, check tolerance, populate CD
    4. Send email to LO with MI and tolerance info
    5. Generate handoff data for Draw Docs
    """
    
    def __init__(self, config: DisclosureConfig, progress_callback: Optional[Callable] = None):
        self.config = config
        self.progress_callback = progress_callback
        self.results = {
            "loan_id": config.loan_id,
            "execution_timestamp": datetime.now().isoformat(),
            "demo_mode": config.demo_mode,
            "agents": {},
            "is_mvp_supported": True,
            "handoff": None,
        }
        
        if self.config.demo_mode:
            os.environ["DRY_RUN"] = "true"
            logger.info("=" * 80)
            logger.info("🔍 DEMO MODE ENABLED - No changes will be written")
            logger.info("=" * 80)
    
    def _run_with_retry(self, agent_func, agent_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Run agent with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"[{agent_name.upper()}] Attempt {attempt + 1}/{self.config.max_retries + 1}")
                
                start_time = time.time()
                result = agent_func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(f"[{agent_name.upper()}] ✓ Success ({elapsed:.1f}s)")
                
                return {
                    "status": "success",
                    "output": result,
                    "attempts": attempt + 1,
                    "elapsed_time": elapsed
                }
                
            except Exception as e:
                logger.error(f"[{agent_name.upper()}] ✗ Attempt {attempt + 1} failed: {e}")
                
                if attempt == self.config.max_retries:
                    logger.error(f"[{agent_name.upper()}] Failed - stopping orchestration")
                    return {
                        "status": "failed",
                        "error": str(e),
                        "attempts": attempt + 1
                    }
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"[{agent_name.upper()}] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
    
    def _check_mvp_eligibility(self, verification_output: Dict[str, Any]) -> bool:
        """Check if loan is MVP eligible based on verification results.
        
        MVP eligible:
        - Loan type: Conventional only
        - State: NV or CA only
        """
        is_mvp_supported = verification_output.get("is_mvp_supported", True)
        loan_type = verification_output.get("loan_type", "Unknown")
        property_state = verification_output.get("property_state", "Unknown")
        
        logger.info(f"[MVP CHECK] Loan Type: {loan_type}, State: {property_state}")
        logger.info(f"[MVP CHECK] MVP Supported: {is_mvp_supported}")
        
        return is_mvp_supported
    
    def run(self) -> Dict[str, Any]:
        """Execute disclosure pipeline.
        
        Returns:
            Dictionary with complete results including handoff data
        """
        logger.info("=" * 80)
        logger.info(f"DISCLOSURE ORCHESTRATOR STARTING (MVP) - Loan {self.config.loan_id}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Verification
            logger.info("[VERIFICATION] Starting")
            verification_result = self._run_with_retry(
                run_disclosure_verification,
                "verification",
                self.config.loan_id
            )
            self.results["agents"]["verification"] = verification_result
            
            if self.progress_callback:
                self.progress_callback("verification", verification_result, self)
            
            if verification_result["status"] == "failed":
                logger.error("[ORCHESTRATOR] Verification failed - stopping")
                return self._finalize_results()
            
            verification_output = verification_result.get("output", {})
            
            # Check MVP eligibility
            is_mvp_supported = self._check_mvp_eligibility(verification_output)
            self.results["is_mvp_supported"] = is_mvp_supported
            self.results["loan_type"] = verification_output.get("loan_type")
            self.results["property_state"] = verification_output.get("property_state")
            
            # Handle non-MVP loans
            if not is_mvp_supported:
                mvp_warnings = verification_output.get("mvp_warnings", [])
                logger.warning("[ORCHESTRATOR] Non-MVP loan detected")
                
                if self.config.skip_non_mvp:
                    logger.warning("[ORCHESTRATOR] Skipping non-MVP loan - manual processing required")
                    self.results["status"] = "manual_required"
                    self.results["manual_reasons"] = mvp_warnings
                    return self._finalize_results()
                else:
                    logger.info("[ORCHESTRATOR] Continuing with non-MVP loan (will flag for review)")
            
            # Step 2: Preparation
            logger.info("[PREPARATION] Starting")
            missing_fields = verification_output.get("fields_missing", [])
            
            preparation_result = self._run_with_retry(
                run_disclosure_preparation,
                "preparation",
                self.config.loan_id,
                missing_fields,
                [],  # fields_to_clean
                self.config.demo_mode
            )
            self.results["agents"]["preparation"] = preparation_result
            
            if self.progress_callback:
                self.progress_callback("preparation", preparation_result, self)
            
            preparation_output = preparation_result.get("output", {})
            
            # Step 3: Request
            logger.info("[REQUEST] Starting")
            
            request_result = self._run_with_retry(
                run_disclosure_request,
                "request",
                self.config.loan_id,
                self.config.lo_email,
                verification_output,
                preparation_output,
                self.config.demo_mode
            )
            self.results["agents"]["request"] = request_result
            
            if self.progress_callback:
                self.progress_callback("request", request_result, self)
            
            # Step 4: Generate handoff for Draw Docs
            logger.info("[HANDOFF] Generating handoff data")
            handoff = create_handoff_from_results(
                self.config.loan_id,
                verification_output,
                preparation_output,
                request_result.get("output"),
            )
            self.results["handoff"] = handoff.to_dict()
            
            logger.info("=" * 80)
            logger.info("DISCLOSURE ORCHESTRATOR COMPLETE")
            logger.info("=" * 80)
            
            return self._finalize_results()
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            self.results["error"] = str(e)
            return self._finalize_results()
    
    def _finalize_results(self) -> Dict[str, Any]:
        """Generate final results with summary."""
        self.results["summary"] = self._generate_summary()
        self.results["json_output"] = self._aggregate_results()
        return self.results
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 80,
            "DISCLOSURE EXECUTION SUMMARY (MVP)",
            "=" * 80,
            f"Loan ID: {self.config.loan_id}",
            f"Timestamp: {self.results['execution_timestamp']}",
            f"Mode: {'DEMO (no actual writes)' if self.config.demo_mode else 'PRODUCTION'}",
            f"MVP Supported: {self.results.get('is_mvp_supported', 'Unknown')}",
            f"Loan Type: {self.results.get('loan_type', 'Unknown')}",
            f"State: {self.results.get('property_state', 'Unknown')}",
            ""
        ]
        
        # Manual required check
        if self.results.get("status") == "manual_required":
            lines.extend([
                "⚠️ MANUAL PROCESSING REQUIRED",
                "-" * 40,
            ])
            for reason in self.results.get("manual_reasons", []):
                lines.append(f"  - {reason}")
            lines.append("")
            return "\n".join(lines)
        
        # Verification
        ver = self.results["agents"].get("verification", {})
        if ver.get("status") == "success":
            ver_output = ver.get("output", {})
            lines.extend([
                "[VERIFICATION AGENT]",
                f"✓ Success ({ver.get('attempts', 1)} attempt(s))",
                f"- Fields checked: {ver_output.get('fields_checked', 0)}",
                f"- Fields missing: {len(ver_output.get('fields_missing', []))}",
                ""
            ])
        else:
            lines.extend([
                "[VERIFICATION AGENT]",
                f"✗ Failed ({ver.get('attempts', 1)} attempt(s))",
                f"- Error: {ver.get('error', 'Unknown')}",
                ""
            ])
        
        # Preparation
        prep = self.results["agents"].get("preparation", {})
        if prep.get("status") == "success":
            prep_output = prep.get("output", {})
            mi_result = prep_output.get("mi_result", {})
            tolerance_result = prep_output.get("tolerance_result", {})
            
            lines.extend([
                "[PREPARATION AGENT]",
                f"✓ Success ({prep.get('attempts', 1)} attempt(s))",
                f"- Fields populated: {len(prep_output.get('fields_populated', []))}",
                f"- Fields cleaned: {len(prep_output.get('fields_cleaned', []))}",
            ])
            
            # MI info
            if mi_result:
                if mi_result.get("requires_mi"):
                    lines.append(f"- MI Monthly: ${mi_result.get('monthly_amount', 0):.2f}")
                else:
                    lines.append("- MI: Not required")
            
            # Tolerance info
            if tolerance_result:
                if tolerance_result.get("has_violations"):
                    lines.append(f"- ⚠️ Tolerance violations: ${tolerance_result.get('total_cure_needed', 0):.2f} cure needed")
                else:
                    lines.append("- Tolerance: No violations")
            
            lines.append("")
        
        # Request
        req = self.results["agents"].get("request", {})
        if req.get("status") == "success":
            req_output = req.get("output", {})
            lines.extend([
                "[REQUEST AGENT]",
                f"✓ Success ({req.get('attempts', 1)} attempt(s))",
                f"- Email sent to: {self.config.lo_email}",
                ""
            ])
        
        # Handoff
        if self.results.get("handoff"):
            handoff = self.results["handoff"]
            lines.extend([
                "[HANDOFF TO DRAW DOCS]",
                f"- Ready for Draw Docs: {not handoff.get('requires_manual', False)}",
            ])
            if handoff.get("requires_manual"):
                lines.append("- ⚠️ Manual processing required")
            lines.append("")
        
        # Overall status
        all_success = all(
            self.results["agents"].get(agent, {}).get("status") == "success"
            for agent in ["verification", "preparation", "request"]
        )
        
        if self.results.get("status") == "manual_required":
            lines.append(f"OVERALL STATUS: MANUAL PROCESSING REQUIRED")
        elif all_success:
            lines.append(f"OVERALL STATUS: SUCCESS")
        else:
            lines.append(f"OVERALL STATUS: PARTIAL FAILURE")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """Aggregate results into JSON format."""
        return {
            "loan_id": self.config.loan_id,
            "timestamp": self.results["execution_timestamp"],
            "demo_mode": self.config.demo_mode,
            "is_mvp_supported": self.results.get("is_mvp_supported"),
            "loan_type": self.results.get("loan_type"),
            "property_state": self.results.get("property_state"),
            "verification": self.results["agents"].get("verification", {}),
            "preparation": self.results["agents"].get("preparation", {}),
            "request": self.results["agents"].get("request", {}),
            "handoff": self.results.get("handoff"),
            "status": self.results.get("status"),
            "manual_reasons": self.results.get("manual_reasons"),
        }


def run_disclosure_orchestrator(
    loan_id: str,
    lo_email: str,
    demo_mode: bool = True,
    max_retries: int = 2,
    skip_non_mvp: bool = False,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Main entry point for disclosure orchestrator.
    
    MVP: Handles Conventional loans in NV/CA only.
    Non-MVP loans are flagged for manual processing.
    
    Args:
        loan_id: Encompass loan GUID
        lo_email: Loan officer email address
        demo_mode: If True, run in dry-run mode
        max_retries: Number of retries per agent
        skip_non_mvp: If True, return early for non-MVP loans
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with complete results including:
        - verification results
        - preparation results (MI, tolerance)
        - request results
        - handoff data for Draw Docs
    """
    config = DisclosureConfig(
        loan_id=loan_id,
        lo_email=lo_email,
        demo_mode=demo_mode,
        max_retries=max_retries,
        skip_non_mvp=skip_non_mvp,
    )
    
    orchestrator = DisclosureOrchestrator(config, progress_callback)
    return orchestrator.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Disclosure Orchestrator Agent (MVP)")
    parser.add_argument("--loan-id", type=str, required=True, help="Loan ID")
    parser.add_argument("--lo-email", type=str, required=True, help="LO email")
    parser.add_argument("--demo", action="store_true", help="Demo mode")
    parser.add_argument("--skip-non-mvp", action="store_true", help="Skip non-MVP loans")
    parser.add_argument("--output", type=str, help="Output JSON file")
    
    args = parser.parse_args()
    
    results = run_disclosure_orchestrator(
        loan_id=args.loan_id,
        lo_email=args.lo_email,
        demo_mode=args.demo,
        skip_non_mvp=args.skip_non_mvp
    )
    
    print("\n" + results.get("summary", ""))
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output}")
