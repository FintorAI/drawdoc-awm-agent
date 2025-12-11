"""
Loan Officer Assistant (LOA) Agent - Main Entry Point

This module provides the main entry point for running the LOA agent.
It orchestrates the workflow: gather data → analyze gaps → present results.

Slice 1 implements Fast Mode (data gap analysis only).
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add LOA directory to path for imports
LOA_DIR = Path(__file__).parent
PROJECT_ROOT = LOA_DIR.parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from state import (
    AgentMode,
    AgentStatus,
    LOAResult,
    LOAState,
    LoanFacts,
    NeedsListResult,
)
from tools.fetch_loan_context import fetch_loan_context
from tools.gap_analyzer import analyze_data_gaps, format_gaps_summary

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def run_loan_officer_agent(
    loan_id: str,
    mode: str = "fast",
    include_write_proposals: bool = False,
) -> LOAResult:
    """
    Execute the Loan Officer Assistant workflow.
    
    This is the main entry point for the LOA agent. It:
    1. Retrieves loan context from Encompass
    2. Analyzes data for completeness gaps (Phase 1)
    3. [Slice 2] Analyzes document coverage gaps (Phase 2)
    4. [Slice 3] Generates human-readable summary via LLM
    
    Args:
        loan_id: Encompass loan GUID
        mode: Execution mode
            - "fast": Data gaps only, skip document processing (~2-5s)
            - "full": Data + document gaps, use cached R&S (~5-15s)
            - "refresh_docs": Trigger new R&S job (~30s-5min)
        include_write_proposals: Whether to generate Encompass field update proposals
        
    Returns:
        LOAResult with loan facts, needs list, and (optionally) summary
        
    Example:
        result = await run_loan_officer_agent(
            loan_id="59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc",
            mode="fast"
        )
        
        print(f"Found {result.needs_list.summary.total} gaps")
        print(f"Critical: {result.needs_list.summary.critical_count}")
        print(f"Can proceed: {result.needs_list.summary.can_proceed}")
    """
    logger.info(f"[LOA] Starting agent for loan {loan_id[:8]}...")
    logger.info(f"[LOA] Mode: {mode}")
    
    # Initialize result
    result = LOAResult(
        loan_id=loan_id,
        mode=mode,
        status=AgentStatus.RUNNING.value,
    )
    
    try:
        # =================================================================
        # PHASE 1: GATHER LOAN CONTEXT
        # =================================================================
        logger.info("[LOA] Phase 1: Gathering loan context...")
        
        loan_facts = await fetch_loan_context(loan_id)
        result.loan_facts = loan_facts
        
        logger.info(f"[LOA] Loan context gathered: {loan_facts.scenario_tag}")
        logger.info(f"[LOA]   - Borrowers: {len(loan_facts.borrowers)}")
        logger.info(f"[LOA]   - eFolder docs: {len(loan_facts.efolder_docs)}")
        
        # =================================================================
        # PHASE 2: ANALYZE DATA GAPS
        # =================================================================
        logger.info("[LOA] Phase 2: Analyzing data gaps...")
        
        needs_list = analyze_data_gaps(loan_facts)
        result.needs_list = needs_list
        
        logger.info(f"[LOA] Data gap analysis complete:")
        logger.info(f"[LOA]   - Total gaps: {needs_list.summary.total}")
        logger.info(f"[LOA]   - Critical: {needs_list.summary.critical_count}")
        logger.info(f"[LOA]   - Can proceed: {needs_list.summary.can_proceed}")
        
        # =================================================================
        # PHASE 3: DOCUMENT COVERAGE (Slice 2 - not implemented yet)
        # =================================================================
        if mode != AgentMode.FAST.value:
            logger.info("[LOA] Phase 3: Document coverage analysis...")
            # TODO (Slice 2): Implement fetch_doc_coverage and analyze_doc_gaps
            logger.warning("[LOA] Document coverage not yet implemented (Slice 2)")
        
        # =================================================================
        # PHASE 4: LLM PRESENTATION (Slice 3 - not implemented yet)
        # =================================================================
        # For now, generate a simple summary
        result.summary = format_gaps_summary(needs_list)
        
        # TODO (Slice 3): Use LLM to generate richer summary
        # result.summary = await present_results(loan_facts, needs_list)
        
        # =================================================================
        # COMPLETE
        # =================================================================
        result.status = AgentStatus.COMPLETE.value
        logger.info("[LOA] ✓ Agent execution complete")
        
    except Exception as e:
        logger.error(f"[LOA] ✗ Agent error: {e}")
        result.status = AgentStatus.ERROR.value
        result.errors.append(str(e))
        import traceback
        traceback.print_exc()
    
    return result


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================

def run_loan_officer_agent_sync(
    loan_id: str,
    mode: str = "fast",
    include_write_proposals: bool = False,
) -> LOAResult:
    """
    Synchronous wrapper for run_loan_officer_agent.
    
    Use this for non-async contexts or testing.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new loop for nested call
            import nest_asyncio
            nest_asyncio.apply()
    except RuntimeError:
        pass
    
    return asyncio.run(run_loan_officer_agent(loan_id, mode, include_write_proposals))


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import json
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage: python -m agents.loan_officer_assistant.agent <loan_id> [mode]")
        print("Example: python -m agents.loan_officer_assistant.agent 59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc fast")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "fast"
    
    print("=" * 70)
    print("LOAN OFFICER ASSISTANT AGENT")
    print("=" * 70)
    print(f"Loan ID: {loan_id}")
    print(f"Mode: {mode}")
    print("=" * 70)
    
    result = run_loan_officer_agent_sync(loan_id, mode)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Status: {result.status}")
    
    if result.errors:
        print(f"Errors: {result.errors}")
    
    if result.loan_facts:
        print(f"\nLoan Type: {result.loan_facts.loan_type}")
        print(f"Loan Purpose: {result.loan_facts.loan_purpose}")
        print(f"Scenario: {result.loan_facts.scenario_tag}")
        print(f"MVP Supported: {result.loan_facts.is_mvp_supported}")
    
    if result.needs_list:
        print(f"\n--- GAP ANALYSIS ---")
        print(f"Total Gaps: {result.needs_list.summary.total}")
        print(f"Critical: {result.needs_list.summary.critical_count}")
        print(f"Warnings: {result.needs_list.summary.warn_count}")
        print(f"Can Proceed: {result.needs_list.summary.can_proceed}")
    
    if result.summary:
        print(f"\n--- SUMMARY ---")
        print(result.summary)
    
    # Save full result to file
    output_file = f"loa_result_{loan_id[:8]}.json"
    with open(output_file, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    print(f"\nFull results saved to: {output_file}")

