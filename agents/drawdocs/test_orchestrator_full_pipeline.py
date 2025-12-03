"""
Test script for the complete 4-agent orchestrator pipeline.

Tests the full workflow:
1. Docs Prep Agent - Extract field values from documents
2. Docs Draw Core Agent - Update Encompass fields
3. Verification Agent - Verify and correct field values
4. Order Docs Agent - Mavent check + Order docs + Delivery
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment from PROJECT ROOT (for working credentials)
from dotenv import load_dotenv
env_file = project_root / ".env"
print(f"Loading environment from: {env_file}\n")
load_dotenv(env_file)

from agents.drawdocs.orchestrator_agent import run_orchestrator

def test_full_pipeline_dry_run():
    """Test the complete 4-agent pipeline in dry-run mode."""
    
    print("\n" + "=" * 80)
    print("FULL PIPELINE TEST - 4 AGENTS")
    print("=" * 80)
    print("\nWorkflow:")
    print("  Step 1: Docs Prep Agent")
    print("  Step 2: Docs Draw Core Agent")
    print("  Step 3: Verification Agent")
    print("  Step 4: Order Docs Agent (NEW - Mavent + Order + Deliver)")
    print("\nMode: DRY RUN (no actual writes)")
    print("=" * 80 + "\n")
    
    # Test loan ID (same as prep test - verified working with fallback)
    loan_id = "8587ad65-e186-4655-b813-f713ff98709f"
    
    # Document types that work perfectly (from successful prep test)
    document_types = ["ID", "Title Report", "Appraisal", "LE", "1003"]
    
    print(f"Loan ID: {loan_id}")
    print(f"Document types: {', '.join(document_types)}")
    print("Starting orchestrator...\n")
    
    # Run orchestrator with specific document types
    result = run_orchestrator(
        loan_id=loan_id,
        document_types=document_types,  # Specify exact document types
        demo_mode=True,
        max_retries=1,
        output_file=None
    )
    
    # Print summary
    if "summary_text" in result:
        print("\n" + result["summary_text"])
    
    # Save detailed results
    output_file = Path(__file__).parent / "test_full_pipeline_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✓ Detailed results saved to: {output_file}")
    print("\n" + "=" * 80)
    
    # Check results
    agents = result.get("agents", {})
    
    print("\nRESULTS SUMMARY:")
    print("-" * 80)
    
    for agent_name, agent_result in agents.items():
        status = agent_result.get("status", "unknown")
        attempts = agent_result.get("attempts", 0)
        symbol = "✓" if status == "success" else "⚠" if status == "partial_success" else "✗"
        print(f"{symbol} {agent_name.upper()}: {status} ({attempts} attempt(s))")
        
        if status == "failed":
            print(f"  Error: {agent_result.get('error', 'Unknown')}")
    
    print("-" * 80)
    
    # Overall success
    all_success = all(
        r.get("status") in ["success", "partial_success"]
        for r in agents.values()
    )
    
    print(f"\nOVERALL: {'✓ SUCCESS' if all_success else '✗ FAILURE'}")
    print("=" * 80 + "\n")
    
    return all_success


def test_orderdocs_only():
    """Test only the Order Docs Agent step."""
    
    print("\n" + "=" * 80)
    print("ORDER DOCS AGENT TEST (STEP 4 ONLY)")
    print("=" * 80)
    print("\nWorkflow:")
    print("  1. Mavent Compliance Check")
    print("  2. Order Documents")
    print("  3. Deliver to eFolder")
    print("\nMode: DRY RUN (no actual writes)")
    print("=" * 80 + "\n")
    
    # Test loan ID
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print(f"Loan ID: {loan_id}")
    print("Starting orchestrator with only orderdocs agent...\n")
    
    # Run orchestrator with only orderdocs agent
    # Skip prep, drawcore, verification to test orderdocs in isolation
    result = run_orchestrator(
        loan_id=loan_id,
        user_prompt="skip preparation, drawcore, verification - only run orderdocs",
        demo_mode=True,
        max_retries=1,
        output_file=None
    )
    
    # Print summary
    if "summary_text" in result:
        print("\n" + result["summary_text"])
    
    # Save detailed results
    output_file = Path(__file__).parent / "test_orderdocs_only_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✓ Detailed results saved to: {output_file}")
    print("\n" + "=" * 80)
    
    return result.get("agents", {}).get("orderdocs", {}).get("status") in ["success", "partial_success"]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test orchestrator with Order Docs Agent")
    parser.add_argument("--full", action="store_true", help="Test full 4-agent pipeline")
    parser.add_argument("--orderdocs-only", action="store_true", help="Test only Order Docs Agent")
    
    args = parser.parse_args()
    
    if args.orderdocs_only:
        success = test_orderdocs_only()
    elif args.full:
        success = test_full_pipeline_dry_run()
    else:
        # Default: run full pipeline
        print("Running full pipeline test (use --orderdocs-only to test Step 4 only)\n")
        success = test_full_pipeline_dry_run()
    
    sys.exit(0 if success else 1)

