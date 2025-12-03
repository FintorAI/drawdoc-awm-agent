#!/usr/bin/env python3
"""
Test script for Docs Draw Core Agent with primitives integration.
READ-ONLY MODE: No writes to Encompass.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from PROJECT ROOT first (for working credentials)
from dotenv import load_dotenv

# Load project root .env FIRST (has working Encompass credentials)
local_env_path = project_root / ".env"
if local_env_path.exists():
    load_dotenv(local_env_path)
    print(f"✅ Loaded project root environment from {local_env_path}")

# Load MCP server .env without override (for any additional settings)
mcp_env_path = Path.home() / "Documents/Fintor/encompass-mcp-server/.env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path, override=False)
    print(f"✅ Loaded MCP server environment from {mcp_env_path}")

# IMPORTANT: Enable DRY RUN mode (no writes!)
os.environ["DRY_RUN"] = "true"

# Now import the drawcore agent
from agents.drawdocs.subagents.drawcore_agent.drawcore_agent import run_drawcore_agent

def test_drawcore_agent():
    """Test the Docs Draw Core Agent with primitives."""
    
    print("\n" + "="*80)
    print("TESTING DOCS DRAW CORE AGENT WITH PRIMITIVES")
    print("="*80)
    print("\nThis test will:")
    print("  1. Load prep output (extracted field values)")
    print("  2. Check loan preconditions")
    print("  3. Run all 5 phases:")
    print("     - Phase 1: Borrower & LO")
    print("     - Phase 2: Contacts & Vendors")
    print("     - Phase 3: Property & Program")
    print("     - Phase 4: Financial Setup")
    print("     - Phase 5: Closing Disclosure")
    print("  4. For each field:")
    print("     - Read current Encompass value")
    print("     - Compare with extracted value")
    print("     - Show update intention (DRY RUN)")
    print("\n⚠️  DRY RUN MODE - NO WRITES TO ENCOMPASS")
    print("="*80)
    
    # Load the sample prep output
    prep_output_path = project_root / "agents/drawdocs/subagents/verification_agent/data/prep_output.json"
    
    if not prep_output_path.exists():
        print(f"\n❌ Error: Sample prep output not found at {prep_output_path}")
        return None
    
    with open(prep_output_path, 'r') as f:
        prep_output = json.load(f)
    
    loan_id = prep_output.get("loan_id", "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6")
    field_mappings = prep_output.get("results", {}).get("field_mappings", {})
    
    print(f"\nLoan ID: {loan_id}")
    print(f"Total extracted fields: {len(field_mappings)}")
    
    if field_mappings:
        print(f"\nSample extracted fields:")
        for i, (field_id, value) in enumerate(list(field_mappings.items())[:5], 1):
            print(f"  {i}. Field {field_id} = {value}")
    
    print("\n" + "="*80)
    print("Running Docs Draw Core Agent...")
    print("="*80 + "\n")
    
    try:
        # Run drawcore agent in DRY RUN mode
        result = run_drawcore_agent(
            loan_id=loan_id,
            doc_context=prep_output,
            dry_run=True  # IMPORTANT: No writes!
        )
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        
        # Print status
        status = result.get("status", "N/A")
        print(f"\nOverall Status: {status.upper()}")
        
        # Print summary
        summary = result.get("summary", {})
        print(f"\n--- Summary ---")
        print(f"Total Fields Processed: {summary.get('total_fields_processed', 0)}")
        print(f"Total Fields Updated (DRY RUN): {summary.get('total_fields_updated', 0)}")
        print(f"Total Issues Logged: {summary.get('total_issues_logged', 0)}")
        print(f"Phases Completed: {summary.get('phases_completed', 0)}/{summary.get('phases_completed', 0) + summary.get('phases_failed', 0)}")
        
        # Print loan context if available
        loan_context = result.get("loan_context", {})
        if loan_context and not loan_context.get("error"):
            print("\n--- Loan Context ---")
            print(f"Loan Number: {loan_context.get('loan_number', 'N/A')}")
            print(f"Loan Type: {loan_context.get('loan_type', 'N/A')}")
            print(f"State: {loan_context.get('state', 'N/A')}")
        
        # Print phase results
        phases = result.get("phases", {})
        if phases:
            print(f"\n--- Phase Results ---")
            for phase_key in sorted(phases.keys()):
                phase_data = phases[phase_key]
                phase_num = phase_key.replace("phase_", "")
                phase_status = phase_data.get("status", "N/A")
                fields_proc = phase_data.get("fields_processed", 0)
                fields_upd = phase_data.get("fields_updated", 0)
                issues = phase_data.get("issues_logged", 0)
                
                status_emoji = "✓" if phase_status == "success" else "⚠️" if phase_status == "partial_success" else "✗"
                
                print(f"\n{status_emoji} Phase {phase_num}: {phase_status.upper()}")
                print(f"   Processed: {fields_proc}, Updated: {fields_upd}, Issues: {issues}")
                
                # Show sample updates from this phase
                updates = phase_data.get("updates", [])
                if updates:
                    print(f"   Sample updates:")
                    for update in updates[:3]:  # Show first 3
                        field_name = update.get("field_name", update.get("field_id"))
                        old_val = update.get("old_value", "None")
                        new_val = update.get("new_value", "None")
                        
                        # Truncate long values
                        old_str = str(old_val)[:30] + "..." if len(str(old_val)) > 30 else str(old_val)
                        new_str = str(new_val)[:30] + "..." if len(str(new_val)) > 30 else str(new_val)
                        
                        print(f"     • {field_name}: {old_str} → {new_str}")
        
        # Save full results to file
        output_file = project_root / "drawcore_agent_test_output.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✅ Full results saved to: {output_file}")
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing drawcore agent: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n⚠️  READ-ONLY TEST - No changes will be made to Encompass")
    print("="*80)
    test_drawcore_agent()

