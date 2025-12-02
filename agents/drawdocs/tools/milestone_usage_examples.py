"""
Milestone API Usage Examples - READ-ONLY MODE

⚠️  IMPORTANT: All examples are READ-ONLY
    No write operations will be performed to avoid modifying your environment.

This file demonstrates:
  ✅ get_loan_context() - Get loan info with milestones
  ✅ get_loan_milestones() - Retrieve all milestones
  ✅ get_milestone_by_name() - Query specific milestones

Write operations are shown as code examples but NOT executed:
  📖 update_milestone_api() - Demo only
  📖 add_milestone_log() - Demo only
  📖 update_milestone() - Demo only (legacy)

To enable write operations:
  1. Uncomment the import statements for write functions
  2. Uncomment the actual function calls in the examples
  3. Make sure you're in a safe test environment!
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from io import StringIO
import traceback as tb

# Add project root to path so we can import from agents
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment from BOTH sources
# Strategy: MCP server FIRST (Encompass OAuth), then local (LandingAI, etc.)

# 1. Load MCP server .env FIRST (for working Encompass credentials)
mcp_env_path = project_root.parent / "encompass-mcp-server" / ".env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path)
    print(f"Loading environment from: {mcp_env_path}")

# 2. Then load local .env WITHOUT override (for LandingAI, DOCREPO, etc.)
fallback_env = project_root / "agents" / "drawdocs" / "subagents" / "preparation_agent" / ".env"
if fallback_env.exists():
    load_dotenv(fallback_env, override=False)
    print(f"Loading environment from: {fallback_env}")
else:
    load_dotenv(override=False)

from agents.drawdocs.tools import (
    get_loan_context,
    get_loan_milestones,
    get_milestone_by_name,
    # Write operations (commented out to avoid modifying environment)
    # update_milestone_api,
    # add_milestone_log,
    # update_milestone,  # Legacy
)


# =============================================================================
# Example 1: Get Loan Context with Milestones
# =============================================================================

def example_get_loan_context_with_milestones():
    """Get comprehensive loan context including full milestone data."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    # Get context with milestones (new approach)
    context = get_loan_context(loan_id, include_milestones=True)
    
    print("Loan Context:")
    print(f"  Loan #: {context['loan_number']}")
    print(f"  Type: {context['loan_type']}")
    print(f"  State: {context['state']}")
    
    print("\nFlags:")
    print(f"  CTC: {context['flags']['is_ctc']}")
    print(f"  CD Approved: {context['flags']['cd_approved']}")
    print(f"  Docs Ordered Finished: {context['flags'].get('docs_ordered_finished', False)}")
    
    # Access milestone data
    if "milestones" in context:
        print("\nMilestone Data:")
        print(f"  Total milestones: {len(context['milestones']['all'])}")
        
        # Check Docs Ordered milestone
        docs_ordered = context['milestones']['docs_ordered']
        if docs_ordered:
            print(f"\n  Docs Ordered:")
            print(f"    Status: {docs_ordered['status']}")
            print(f"    Date: {docs_ordered.get('statusDate', 'N/A')}")
            print(f"    Comment: {docs_ordered.get('comment', 'N/A')}")


# =============================================================================
# Example 2: Get All Milestones
# =============================================================================

def example_get_all_milestones():
    """Get and display all milestones for a loan."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    milestones = get_loan_milestones(loan_id)
    
    print(f"Found {len(milestones)} milestones:")
    print()
    
    for milestone in milestones:
        print(f"- {milestone.get('milestoneName')}")
        print(f"  Status: {milestone.get('status')}")
        print(f"  Date: {milestone.get('statusDate', 'N/A')}")
        
        # Show logs if any
        logs = milestone.get('logs', [])
        if logs:
            print(f"  Logs: {len(logs)} entries")
            for log in logs[:2]:  # Show first 2 logs
                print(f"    • {log.get('comment', 'N/A')} ({log.get('date', 'N/A')})")
        
        print()


# =============================================================================
# Example 3: Get Specific Milestone
# =============================================================================

def example_get_specific_milestone():
    """Get a specific milestone by name."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    # Get "Docs Ordered" milestone
    docs_ordered = get_milestone_by_name(loan_id, "Docs Ordered")
    
    if docs_ordered:
        print("Docs Ordered Milestone:")
        print(f"  ID: {docs_ordered.get('id')}")
        print(f"  Status: {docs_ordered.get('status')}")
        print(f"  Status Date: {docs_ordered.get('statusDate')}")
        print(f"  Comment: {docs_ordered.get('comment', 'None')}")
        
        # Check if finished
        if docs_ordered.get('status') == 'Finished':
            print("  ✓ Milestone is complete!")
        else:
            print(f"  ⏳ Milestone is {docs_ordered.get('status')}")
    else:
        print("❌ 'Docs Ordered' milestone not found")


# =============================================================================
# Example 4: Update Milestone (New API Method) - READ-ONLY DEMO
# =============================================================================

def example_update_milestone_api():
    """DEMO: How to update a milestone (no actual write performed)."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("📖 READ-ONLY DEMO: How to update a milestone")
    print()
    
    # Show current status
    docs_ordered = get_milestone_by_name(loan_id, "Docs Ordered")
    if docs_ordered:
        print(f"Current status: {docs_ordered.get('status')}")
        print(f"Current comment: {docs_ordered.get('comment', 'None')}")
    
    print()
    print("To update (code example - NOT executed):")
    print("""
    from agents.drawdocs.tools import update_milestone_api
    
    success = update_milestone_api(
        loan_id=loan_id,
        milestone_name="Docs Ordered",
        status="Finished",
        comment="DOCS Out on 12/01/2025"
    )
    """)
    
    print("⚠️  Actual update NOT performed (read-only mode)")


# =============================================================================
# Example 5: Add Milestone Log - READ-ONLY DEMO
# =============================================================================

def example_add_milestone_log():
    """DEMO: How to add a log entry to a milestone (no actual write)."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("📖 READ-ONLY DEMO: How to add milestone logs")
    print()
    
    # Show current logs
    docs_ordered = get_milestone_by_name(loan_id, "Docs Ordered")
    if docs_ordered:
        logs = docs_ordered.get('logs', [])
        print(f"Current logs: {len(logs)} entries")
        if logs:
            print("\nMost recent logs:")
            for log in logs[-3:]:  # Show last 3
                print(f"  • {log.get('comment', 'N/A')}")
                print(f"    Date: {log.get('date', 'N/A')}")
    
    print()
    print("To add a log (code example - NOT executed):")
    print("""
    from agents.drawdocs.tools import add_milestone_log
    
    success = add_milestone_log(
        loan_id=loan_id,
        milestone_name="Docs Ordered",
        comment="Documents sent to title company",
        done_by="AutomationAgent"
    )
    """)
    
    print("⚠️  Actual log NOT added (read-only mode)")


# =============================================================================
# Example 6: Legacy vs New Approach Comparison - READ-ONLY
# =============================================================================

def example_legacy_vs_new():
    """Compare legacy field-based vs new API-based approaches (read-only)."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("📖 COMPARISON: Legacy vs New Approach (Read-Only)")
    print("=" * 60)
    
    print("\nLEGACY APPROACH (Field-Based):")
    print("-" * 60)
    print("Code example:")
    print("""
    update_milestone(
        loan_id=loan_id,
        status="Finished",
        comment="DOCS Out on 12/01/2025"
    )
    """)
    print("Limitations:")
    print("  ❌ Only updates hardcoded 'Docs Out' fields")
    print("  ❌ No access to milestone history")
    print("  ❌ Can't query milestone status")
    print("  ❌ Can't work with other milestones")
    
    print("\nNEW APPROACH (API-Based):")
    print("-" * 60)
    print("Code example:")
    print("""
    update_milestone_api(
        loan_id=loan_id,
        milestone_name="Docs Ordered",  # Any milestone!
        status="Finished",
        comment="DOCS Out on 12/01/2025"
    )
    """)
    print("Benefits:")
    print("  ✅ Works with ANY milestone name")
    print("  ✅ Full milestone history available")
    print("  ✅ Can query status, logs, dates")
    print("  ✅ Can add logs independently")
    
    # Show current milestone data (read-only)
    print("\nCurrent Milestone Data (from API):")
    print("-" * 60)
    docs_ordered = get_milestone_by_name(loan_id, "Docs Ordered")
    if docs_ordered:
        print(f"Milestone: {docs_ordered.get('milestoneName')}")
        print(f"Status: {docs_ordered.get('status')}")
        print(f"Last Updated: {docs_ordered.get('statusDate', 'N/A')}")
        print(f"Comment: {docs_ordered.get('comment', 'None')}")
        print(f"Logs: {len(docs_ordered.get('logs', []))} entries")
    else:
        print("Milestone not found")
    
    print("\n⚠️  No writes performed (read-only mode)")


# =============================================================================
# Example 7: Workflow - Complete Docs Ordered Process - READ-ONLY DEMO
# =============================================================================

def example_complete_docs_ordered_workflow():
    """DEMO: Complete workflow for marking Docs Ordered as finished (read-only)."""
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("📖 DOCS ORDERED WORKFLOW DEMO (Read-Only)")
    print("=" * 60)
    
    # Step 1: Check preconditions
    print("\n1. Checking preconditions...")
    context = get_loan_context(loan_id, include_milestones=True)
    
    if not context['flags']['is_ctc']:
        print("  ❌ Loan is not Clear to Close")
        print("     (Would stop here in real workflow)")
    else:
        print("  ✓ Loan is CTC")
    
    # Step 2: Check current status
    print("\n2. Checking Docs Ordered status...")
    docs_ordered = context['milestones'].get('docs_ordered')
    if not docs_ordered:
        print("  ❌ Docs Ordered milestone not found")
        return
    
    print(f"  Current status: {docs_ordered.get('status')}")
    print(f"  Current comment: {docs_ordered.get('comment', 'None')}")
    print(f"  Status date: {docs_ordered.get('statusDate', 'N/A')}")
    
    # Step 3: DEMO - Would update to Finished
    print("\n3. [DEMO] Would update milestone to Finished...")
    print("  Code that would run:")
    print("""
    update_milestone_api(
        loan_id=loan_id,
        milestone_name="Docs Ordered",
        status="Finished",
        comment=f"DOCS Out on {datetime.now().strftime('%m/%d/%Y')}"
    )
    """)
    print("  ⚠️  NOT executed (read-only mode)")
    
    # Step 4: DEMO - Would add log entry
    print("\n4. [DEMO] Would add log entry...")
    print("  Code that would run:")
    print("""
    add_milestone_log(
        loan_id=loan_id,
        milestone_name="Docs Ordered",
        comment="Documents generated and sent to title company",
        done_by="DocsDrawAgent"
    )
    """)
    print("  ⚠️  NOT executed (read-only mode)")
    
    # Step 5: Show what logs exist
    print("\n5. Current logs...")
    logs = docs_ordered.get('logs', [])
    print(f"  Total logs: {len(logs)}")
    if logs:
        print("  Most recent:")
        for log in logs[-2:]:
            print(f"    • {log.get('comment', 'N/A')}")
            print(f"      Date: {log.get('date', 'N/A')}")
    
    print("\n📋 WORKFLOW DEMO COMPLETE (no changes made)")


# =============================================================================
# Main - Run Examples
# =============================================================================

if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    # Initialize results collection
    results = {
        "timestamp": datetime.now().isoformat(),
        "mode": "READ-ONLY",
        "examples": [],
        "summary": {}
    }
    
    print("\n" + "=" * 80)
    print("MILESTONE API EXAMPLES - READ-ONLY MODE")
    print("=" * 80)
    print("\n⚠️  All examples are READ-ONLY - no writes will be performed")
    print("This ensures your environment remains unchanged.\n")
    
    # Check if MCP client is available
    from agents.drawdocs.tools.primitives import MCP_HTTP_CLIENT_AVAILABLE
    
    results["mcp_client_available"] = MCP_HTTP_CLIENT_AVAILABLE
    
    if not MCP_HTTP_CLIENT_AVAILABLE:
        print("⚠️  WARNING: MCP HTTP client not available")
        print("Place encompass-mcp-server in parent directory to enable milestone API.")
        print()
    else:
        print("✅ MCP HTTP client available - milestone API ready")
        print()
    
    # Run examples
    examples = [
        ("Get Loan Context with Milestones", example_get_loan_context_with_milestones),
        ("Get All Milestones", example_get_all_milestones),
        ("Get Specific Milestone", example_get_specific_milestone),
        ("Update Milestone Demo (Read-Only)", example_update_milestone_api),
        ("Add Milestone Log Demo (Read-Only)", example_add_milestone_log),
        ("Legacy vs New Comparison", example_legacy_vs_new),
        ("Complete Workflow Demo (Read-Only)", example_complete_docs_ordered_workflow),
    ]
    
    successful = 0
    failed = 0
    
    for idx, (name, func) in enumerate(examples, 1):
        print(f"\n{'=' * 80}")
        print(f"Example {idx}: {name}")
        print("=" * 80)
        
        example_result = {
            "id": idx,
            "name": name,
            "status": "success",
            "output": None,
            "error": None
        }
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            func()
            example_result["output"] = captured_output.getvalue()
            successful += 1
        except Exception as e:
            example_result["status"] = "error"
            example_result["error"] = str(e)
            example_result["traceback"] = tb.format_exc()
            example_result["output"] = captured_output.getvalue()
            failed += 1
        finally:
            # Restore stdout
            sys.stdout = old_stdout
            
        # Print to console
        if example_result["output"]:
            print(example_result["output"])
        if example_result["error"]:
            print(f"❌ Error: {example_result['error']}")
        
        results["examples"].append(example_result)
        
        if idx < len(examples):
            print("\n")
    
    # Add summary
    results["summary"] = {
        "total": len(examples),
        "successful": successful,
        "failed": failed
    }
    
    # Save to JSON file
    output_file = project_root / "milestone_examples_output.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✅ All examples completed (read-only mode)")
    print(f"📄 Results saved to: {output_file}")
    print(f"📊 Summary: {successful} successful, {failed} failed")
    print("=" * 80)

