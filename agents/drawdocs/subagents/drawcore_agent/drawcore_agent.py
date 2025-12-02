#!/usr/bin/env python3
"""
Docs Draw Core Agent - Main field update agent.

This agent is the heart of the docs draw system. It takes the extracted data
from the Prep Agent and updates Encompass fields across 5 phases:

1. Phase 1: Borrower & LO - Borrower names, vesting, loan officer info
2. Phase 2: Contacts & Vendors - Title company, escrow, lenders, etc.
3. Phase 3: Property & Program - FHA/VA/USDA case numbers, property details
4. Phase 4: Financial Setup - Terms, rates, fees, escrow, itemization
5. Phase 5: Closing Disclosure - CD pages with final numbers

Each phase:
- Reads current Encompass fields (via primitives)
- Compares extracted values vs current values
- Updates fields OR flags discrepancies
- Logs all actions for audit trail

Features:
- Uses primitives for all Encompass I/O
- Dry run mode (no actual writes)
- Comprehensive logging and reporting
- Handles missing/ambiguous data gracefully
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import primitives
from agents.drawdocs.tools.primitives import (
    get_loan_context,
    read_fields,
    write_fields,
    log_issue,
)

# Import phase processors
from agents.drawdocs.subagents.drawcore_agent.phases.phase1_borrower_lo import (
    process_borrower_lo_phase
)
from agents.drawdocs.subagents.drawcore_agent.phases.phase2_contacts import (
    process_contacts_phase
)
from agents.drawdocs.subagents.drawcore_agent.phases.phase3_property import (
    process_property_phase
)
from agents.drawdocs.subagents.drawcore_agent.phases.phase4_financial import (
    process_financial_phase
)
from agents.drawdocs.subagents.drawcore_agent.phases.phase5_cd import (
    process_cd_phase
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# MAIN AGENT
# =============================================================================

def run_drawcore_agent(
    loan_id: str,
    doc_context: Dict[str, Any],
    dry_run: bool = True,
    phases_to_run: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Run the Docs Draw Core Agent.
    
    Args:
        loan_id: Encompass loan GUID
        doc_context: Output from Prep Agent containing extracted field values
        dry_run: If True, don't actually write to Encompass (default: True)
        phases_to_run: Optional list of phase numbers to run (1-5). If None, runs all.
        
    Returns:
        Dictionary with:
            - loan_id
            - status: "success" | "partial_success" | "failed"
            - phases: Results from each phase
            - summary: Overall summary of updates/issues
            - loan_context: Loan precondition info
            - error: Error message if failed
            
    Example:
        >>> result = run_drawcore_agent(
        ...     loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
        ...     doc_context=prep_agent_output,
        ...     dry_run=True
        ... )
    """
    logger.info("=" * 80)
    logger.info("DOCS DRAW CORE AGENT - Starting")
    logger.info("=" * 80)
    logger.info(f"Loan ID: {loan_id}")
    logger.info(f"Dry Run: {dry_run}")
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be written to Encompass")
    else:
        logger.warning("⚠️  PRODUCTION MODE - Changes WILL be written to Encompass")
    
    result = {
        "loan_id": loan_id,
        "execution_timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "status": "in_progress",
        "phases": {},
        "summary": {
            "total_fields_processed": 0,
            "total_fields_updated": 0,
            "total_issues_logged": 0,
            "phases_completed": 0,
            "phases_failed": 0
        },
        "loan_context": None,
        "error": None
    }
    
    try:
        # Step 1: Check loan preconditions
        logger.info("\nChecking loan preconditions...")
        try:
            loan_context = get_loan_context(loan_id)
            result["loan_context"] = loan_context
            logger.info(f"✓ Loan context retrieved: {loan_context.get('loan_number', 'N/A')}")
        except Exception as e:
            logger.warning(f"⚠️  Could not retrieve loan context: {e}")
            result["loan_context"] = {"error": str(e)}
        
        # Determine which phases to run
        if phases_to_run is None:
            phases_to_run = [1, 2, 3, 4, 5]
        
        logger.info(f"\nPhases to run: {phases_to_run}")
        
        # Phase definitions
        phase_processors = {
            1: ("Borrower & LO", process_borrower_lo_phase),
            2: ("Contacts & Vendors", process_contacts_phase),
            3: ("Property & Program", process_property_phase),
            4: ("Financial Setup", process_financial_phase),
            5: ("Closing Disclosure", process_cd_phase)
        }
        
        # Run each phase
        for phase_num in phases_to_run:
            if phase_num not in phase_processors:
                logger.warning(f"⚠️  Unknown phase: {phase_num}, skipping...")
                continue
            
            phase_name, phase_processor = phase_processors[phase_num]
            
            logger.info("\n" + "=" * 80)
            logger.info(f"PHASE {phase_num}: {phase_name}")
            logger.info("=" * 80)
            
            try:
                phase_result = phase_processor(
                    loan_id=loan_id,
                    doc_context=doc_context,
                    dry_run=dry_run
                )
                
                result["phases"][f"phase_{phase_num}"] = phase_result
                
                # Update summary
                result["summary"]["total_fields_processed"] += phase_result.get("fields_processed", 0)
                result["summary"]["total_fields_updated"] += phase_result.get("fields_updated", 0)
                result["summary"]["total_issues_logged"] += phase_result.get("issues_logged", 0)
                
                if phase_result.get("status") == "success":
                    result["summary"]["phases_completed"] += 1
                    logger.info(f"✓ Phase {phase_num} completed successfully")
                else:
                    result["summary"]["phases_failed"] += 1
                    logger.warning(f"⚠️  Phase {phase_num} completed with issues")
                
            except Exception as e:
                logger.error(f"✗ Phase {phase_num} failed: {e}")
                result["phases"][f"phase_{phase_num}"] = {
                    "status": "failed",
                    "error": str(e),
                    "fields_processed": 0,
                    "fields_updated": 0,
                    "issues_logged": 0
                }
                result["summary"]["phases_failed"] += 1
                
                # Log issue
                try:
                    log_issue(
                        loan_id=loan_id,
                        issue_type="error",
                        message=f"Phase {phase_num} ({phase_name}) failed: {str(e)}",
                        field_id=None
                    )
                except Exception as log_error:
                    logger.error(f"Could not log issue: {log_error}")
        
        # Determine overall status
        if result["summary"]["phases_failed"] == 0:
            result["status"] = "success"
        elif result["summary"]["phases_completed"] > 0:
            result["status"] = "partial_success"
        else:
            result["status"] = "failed"
            result["error"] = "All phases failed"
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("DOCS DRAW CORE AGENT - Summary")
        logger.info("=" * 80)
        logger.info(f"Status: {result['status'].upper()}")
        logger.info(f"Fields Processed: {result['summary']['total_fields_processed']}")
        logger.info(f"Fields Updated: {result['summary']['total_fields_updated']}")
        logger.info(f"Issues Logged: {result['summary']['total_issues_logged']}")
        logger.info(f"Phases Completed: {result['summary']['phases_completed']}/{len(phases_to_run)}")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"\n✗ FATAL ERROR: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
        
        # Log critical issue
        try:
            log_issue(
                loan_id=loan_id,
                issue_type="error",
                message=f"Docs Draw Core Agent failed: {str(e)}",
                field_id=None
            )
        except Exception as log_error:
            logger.error(f"Could not log critical issue: {log_error}")
        
        return result


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Docs Draw Core Agent - Main field update agent"
    )
    parser.add_argument(
        "--loan-id",
        required=True,
        help="Encompass loan GUID"
    )
    parser.add_argument(
        "--doc-context",
        required=True,
        help="Path to doc_context JSON file (from Prep Agent)"
    )
    parser.add_argument(
        "--output",
        help="Output file path for results (JSON)"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run in PRODUCTION mode (actually write to Encompass). Default is DRY RUN."
    )
    parser.add_argument(
        "--phases",
        help="Comma-separated list of phase numbers to run (1-5). Default: all"
    )
    
    args = parser.parse_args()
    
    # Load doc_context
    with open(args.doc_context, 'r') as f:
        doc_context = json.load(f)
    
    # Parse phases
    phases_to_run = None
    if args.phases:
        phases_to_run = [int(p.strip()) for p in args.phases.split(',')]
    
    # Run agent
    result = run_drawcore_agent(
        loan_id=args.loan_id,
        doc_context=doc_context,
        dry_run=not args.production,
        phases_to_run=phases_to_run
    )
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\n✅ Results saved to: {output_path}")
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] in ["success", "partial_success"] else 1)

