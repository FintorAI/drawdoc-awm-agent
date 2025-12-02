"""Disclosure Orchestrator Agent (v2).

v2: Focus on Initial LE disclosure with mandatory compliance checks.

Workflow:
1. Verification: TRID compliance, form validation, MVP eligibility
2. Preparation: RegZ-LE updates, MI calculation, CTC matching
3. Send: Mavent check, ATR/QM check, order eDisclosures
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
from agents.disclosure.subagents.send_agent.send_agent import run_disclosure_send

# Import shared utilities
from packages.shared import (
    get_loan_type,
    LoanType,
    PropertyState,
    MVPExclusions,
    # Pre-check functions
    run_pre_check,
    PreCheckResult,
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
    """Orchestrator for disclosure agent pipeline (v2).
    
    v2 workflow:
    0. PRE-CHECK: Milestone, disclosure tracking, eligibility check
    1. Verify: TRID compliance, form validation, MVP eligibility
    2. Preparation: RegZ-LE updates, MI calculation, CTC matching
    3. Send: Mavent check, ATR/QM check, order eDisclosures
    
    Blocking conditions (early exit):
    - Initial LE already sent (from disclosure tracking)
    - Loan in terminal status (Funded, Closed, etc.)
    - Non-Conventional loan type
    - Texas property
    - LE Due Date passed
    - Application Date not set
    """
    
    def __init__(self, config: DisclosureConfig, progress_callback: Optional[Callable] = None):
        self.config = config
        self.progress_callback = progress_callback
        self.results = {
            "loan_id": config.loan_id,
            "execution_timestamp": datetime.now().isoformat(),
            "demo_mode": config.demo_mode,
            "disclosure_type": "initial_le",  # v2: LE focus
            "agents": {},
            "pre_check": None,  # Pre-check results
            "is_mvp_supported": True,
            "blocking_issues": [],
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
        """Execute disclosure pipeline (v2).
        
        Returns:
            Dictionary with complete results including tracking ID
        """
        logger.info("=" * 80)
        logger.info(f"DISCLOSURE ORCHESTRATOR STARTING (v2 - LE Focus) - Loan {self.config.loan_id}")
        logger.info("=" * 80)
        
        try:
            # Step 0: PRE-CHECK (milestone, disclosure tracking, eligibility)
            logger.info("[PRE-CHECK] Running eligibility checks...")
            pre_check_result = run_pre_check(self.config.loan_id)
            self.results["pre_check"] = pre_check_result.to_dict()
            
            if self.progress_callback:
                self.progress_callback("pre_check", pre_check_result.to_dict(), self)
            
            # Check for pre-check blocking issues
            if not pre_check_result.can_proceed:
                logger.error(f"[PRE-CHECK] BLOCKED: {pre_check_result.blocking_reasons}")
                self.results["blocking_issues"].extend(pre_check_result.blocking_reasons)
                self.results["status"] = "blocked"
                
                if self.config.skip_non_mvp:
                    logger.warning("[ORCHESTRATOR] Stopping due to pre-check blocking")
                    return self._finalize_results()
            
            # Log pre-check results
            if pre_check_result.disclosure_tracking.success:
                if pre_check_result.disclosure_tracking.le_already_sent:
                    logger.warning("[PRE-CHECK] Initial LE already sent - this is COC/Revised LE")
                else:
                    logger.info("[PRE-CHECK] No LE sent yet - eligible for Initial LE")
            
            if pre_check_result.milestones_api.success:
                logger.info(f"[PRE-CHECK] Current milestone: {pre_check_result.milestones_api.current_milestone}")
            
            # Add warnings to results
            if pre_check_result.warnings:
                self.results["pre_check_warnings"] = pre_check_result.warnings
            
            # Step 1: Verification (v2: includes TRID, form checks)
            logger.info("[VERIFICATION] Starting (v2)")
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
            
            # Check MVP eligibility (v2: includes Texas exclusion)
            is_mvp_supported = self._check_mvp_eligibility(verification_output)
            self.results["is_mvp_supported"] = is_mvp_supported
            self.results["loan_type"] = verification_output.get("loan_type")
            self.results["property_state"] = verification_output.get("property_state")
            
            # v2: Check for blocking issues from verification
            blocking_issues = verification_output.get("blocking_issues", [])
            self.results["blocking_issues"].extend(blocking_issues)
            
            # v2: Check TRID compliance
            trid_result = verification_output.get("trid_compliance", {})
            if trid_result.get("is_past_due"):
                blocking_issues.append("LE Due Date PASSED - Escalate to Supervisor")
            
            # Handle blocking conditions
            if blocking_issues:
                logger.warning(f"[ORCHESTRATOR] Blocking issues detected: {blocking_issues}")
                self.results["status"] = "blocked"
                self.results["blocking_issues"] = blocking_issues
                
                if self.config.skip_non_mvp:
                    logger.warning("[ORCHESTRATOR] Stopping due to blocking issues")
                    return self._finalize_results()
            
            # Handle non-MVP loans
            if not is_mvp_supported:
                logger.warning("[ORCHESTRATOR] Non-MVP loan detected")
                
                if self.config.skip_non_mvp:
                    logger.warning("[ORCHESTRATOR] Skipping non-MVP loan - manual processing required")
                    self.results["status"] = "manual_required"
                    return self._finalize_results()
                else:
                    logger.info("[ORCHESTRATOR] Continuing with non-MVP loan (will flag for review)")
            
            # Step 2: Preparation (v2: includes RegZ-LE, CTC)
            logger.info("[PREPARATION] Starting (v2)")
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
            
            # Step 3: Send (v2: replaces Request with Mavent, ATR/QM, eDisclosures)
            logger.info("[SEND] Starting (v2)")
            
            send_result = self._run_with_retry(
                run_disclosure_send,
                "send",
                self.config.loan_id,
                self.config.demo_mode
            )
            self.results["agents"]["send"] = send_result
            
            if self.progress_callback:
                self.progress_callback("send", send_result, self)
            
            send_output = send_result.get("output", {})
            
            # v2: Store tracking ID if ordered
            if send_output.get("tracking_id"):
                self.results["tracking_id"] = send_output.get("tracking_id")
            
            # v2: Collect blocking issues from Send agent
            send_blocking = send_output.get("blocking_issues", [])
            self.results["blocking_issues"].extend(send_blocking)
            
            logger.info("=" * 80)
            logger.info("DISCLOSURE ORCHESTRATOR COMPLETE (v2)")
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
        """Generate human-readable summary (v2)."""
        lines = [
            "=" * 80,
            "DISCLOSURE EXECUTION SUMMARY (v2 - LE Focus)",
            "=" * 80,
            f"Loan ID: {self.config.loan_id}",
            f"Timestamp: {self.results['execution_timestamp']}",
            f"Mode: {'DEMO (no actual writes)' if self.config.demo_mode else 'PRODUCTION'}",
            f"Disclosure Type: {self.results.get('disclosure_type', 'initial_le')}",
            f"MVP Supported: {self.results.get('is_mvp_supported', 'Unknown')}",
            f"Loan Type: {self.results.get('loan_type', 'Unknown')}",
            f"State: {self.results.get('property_state', 'Unknown')}",
            ""
        ]
        
        # Pre-check results
        pre_check = self.results.get("pre_check")
        if pre_check:
            lines.extend([
                "[PRE-CHECK]",
            ])
            if pre_check.get("can_proceed"):
                lines.append("✓ Eligible for disclosure")
            else:
                lines.append("✗ NOT eligible - blocked")
            
            # Disclosure tracking
            dt = pre_check.get("disclosure_tracking", {})
            if dt.get("success"):
                if dt.get("le_already_sent"):
                    lines.append("• Disclosure Tracking: LE already sent (COC/Revised)")
                else:
                    lines.append("• Disclosure Tracking: No LE sent - eligible for Initial LE")
            
            # Milestone
            ms = pre_check.get("milestones_api", {})
            if ms.get("success"):
                lines.append(f"• Current Milestone: {ms.get('current_milestone', 'Unknown')}")
            
            # Status
            mc = pre_check.get("milestone_check", {})
            if mc:
                lines.append(f"• Loan Status: {mc.get('current_status', 'Unknown')}")
            
            lines.append("")
        
        # Blocking issues
        if self.results.get("blocking_issues"):
            lines.extend([
                "⚠️ BLOCKING ISSUES DETECTED",
                "-" * 40,
            ])
            for issue in self.results.get("blocking_issues", []):
                lines.append(f"  - {issue}")
            lines.append("")
        
        # Manual required check
        if self.results.get("status") == "manual_required":
            lines.extend([
                "⚠️ MANUAL PROCESSING REQUIRED",
                "-" * 40,
            ])
            lines.append("")
            return "\n".join(lines)
        
        # Verification
        ver = self.results["agents"].get("verification", {})
        if ver.get("status") == "success":
            ver_output = ver.get("output", {})
            trid = ver_output.get("trid_compliance", {})
            lines.extend([
                "[VERIFICATION AGENT (v2)]",
                f"✓ Success ({ver.get('attempts', 1)} attempt(s))",
                f"- TRID: {'Compliant' if trid.get('compliant') else 'Issues detected'}",
                f"- Fields checked: {ver_output.get('fields_checked', 0)}",
                f"- Fields missing: {len(ver_output.get('fields_missing', []))}",
                ""
            ])
        else:
            lines.extend([
                "[VERIFICATION AGENT (v2)]",
                f"✗ Failed ({ver.get('attempts', 1)} attempt(s))",
                f"- Error: {ver.get('error', 'Unknown')}",
                ""
            ])
        
        # Preparation
        prep = self.results["agents"].get("preparation", {})
        if prep.get("status") == "success":
            prep_output = prep.get("output", {})
            regz_le_result = prep_output.get("regz_le_result", {})
            mi_result = prep_output.get("mi_result", {})
            ctc_result = prep_output.get("ctc_result", {})
            
            lines.extend([
                "[PREPARATION AGENT (v2)]",
                f"✓ Success ({prep.get('attempts', 1)} attempt(s))",
            ])
            
            # RegZ-LE
            if regz_le_result:
                lines.append(f"- RegZ-LE: {len(regz_le_result.get('updates_made', {}))} fields updated")
            
            # MI info
            if mi_result:
                if mi_result.get("requires_mi"):
                    lines.append(f"- MI Monthly: ${mi_result.get('monthly_amount', 0):.2f}")
                else:
                    lines.append("- MI: Not required (LTV ≤ 80%)")
            
            # CTC info
            if ctc_result:
                if ctc_result.get("matched"):
                    lines.append(f"- CTC: Matched ${ctc_result.get('calculated_ctc', 0):,.2f}")
                else:
                    lines.append("- CTC: ⚠️ Mismatch detected")
            
            lines.append("")
        
        # Send (v2: replaces Request)
        send = self.results["agents"].get("send", {})
        if send.get("status") == "success":
            send_output = send.get("output", {})
            mavent = send_output.get("mavent_result", {})
            atr_qm = send_output.get("atr_qm_result", {})
            order = send_output.get("order_result", {})
            
            lines.extend([
                "[SEND AGENT (v2)]",
                f"✓ Success ({send.get('attempts', 1)} attempt(s))",
            ])
            
            # Mavent
            if mavent:
                if mavent.get("passed"):
                    lines.append("- Mavent: PASSED")
                else:
                    lines.append(f"- Mavent: ⚠️ {mavent.get('total_issues', 0)} issues")
            
            # ATR/QM
            if atr_qm:
                if atr_qm.get("passed"):
                    lines.append("- ATR/QM: All flags acceptable")
                else:
                    lines.append(f"- ATR/QM: ⚠️ Red flags: {atr_qm.get('red_flags', [])}")
            
            # Order
            if order and order.get("success"):
                lines.append(f"- Disclosure Ordered! Tracking ID: {order.get('tracking_id', 'N/A')}")
            elif self.config.demo_mode:
                lines.append("- [DRY RUN - Disclosure not ordered]")
            
            lines.append("")
        
        # Tracking ID
        if self.results.get("tracking_id"):
            lines.extend([
                "[DISCLOSURE TRACKING]",
                f"Tracking ID: {self.results['tracking_id']}",
                ""
            ])
        
        # Overall status
        all_success = all(
            self.results["agents"].get(agent, {}).get("status") == "success"
            for agent in ["verification", "preparation", "send"]
        )
        
        if self.results.get("status") == "blocked":
            lines.append(f"OVERALL STATUS: BLOCKED - See blocking issues above")
        elif self.results.get("status") == "manual_required":
            lines.append(f"OVERALL STATUS: MANUAL PROCESSING REQUIRED")
        elif all_success:
            lines.append(f"OVERALL STATUS: SUCCESS")
        else:
            lines.append(f"OVERALL STATUS: PARTIAL FAILURE")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """Aggregate results into JSON format (v2)."""
        return {
            "loan_id": self.config.loan_id,
            "timestamp": self.results["execution_timestamp"],
            "demo_mode": self.config.demo_mode,
            "disclosure_type": self.results.get("disclosure_type", "initial_le"),
            "is_mvp_supported": self.results.get("is_mvp_supported"),
            "loan_type": self.results.get("loan_type"),
            "property_state": self.results.get("property_state"),
            # Pre-check results (integrated)
            "pre_check": self.results.get("pre_check"),
            # v2: Agent results
            "verification": self.results["agents"].get("verification", {}),
            "preparation": self.results["agents"].get("preparation", {}),
            "send": self.results["agents"].get("send", {}),  # v2: replaces "request"
            # v2: New fields
            "tracking_id": self.results.get("tracking_id"),
            "blocking_issues": self.results.get("blocking_issues", []),
            "status": self.results.get("status"),
        }


def run_disclosure_orchestrator(
    loan_id: str,
    lo_email: str = "",
    demo_mode: bool = True,
    max_retries: int = 2,
    skip_non_mvp: bool = False,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Main entry point for disclosure orchestrator (v2).
    
    v2: Focus on Initial LE disclosure with mandatory compliance checks.
    - Runs PRE-CHECK first (milestones, disclosure tracking, eligibility)
    - Conventional loans only (FHA/VA/USDA require manual)
    - NOT Texas (special state rules)
    
    Workflow:
    0. Pre-check: milestone status, disclosure tracking, loan eligibility
    1. Verification: TRID compliance, form validation, MVP eligibility
    2. Preparation: RegZ-LE updates, MI calculation, CTC matching
    3. Send: Mavent check, ATR/QM check, order eDisclosures
    
    Args:
        loan_id: Encompass loan GUID
        lo_email: Loan officer email address (optional in v2)
        demo_mode: If True, run in dry-run mode
        max_retries: Number of retries per agent
        skip_non_mvp: If True, return early for non-MVP/blocked loans
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with complete results including:
        - pre_check results (milestone, disclosure tracking)
        - verification results (TRID, forms)
        - preparation results (RegZ-LE, MI, CTC)
        - send results (Mavent, ATR/QM, order)
        - tracking_id (if disclosure ordered)
        - blocking_issues (if any)
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
