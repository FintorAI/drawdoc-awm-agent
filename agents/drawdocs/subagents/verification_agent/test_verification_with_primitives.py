#!/usr/bin/env python3
"""
Test script for Verification Agent with primitives integration.
READ-ONLY MODE: No writes to Encompass.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv

# Load from MCP server first, then local (local won't override)
mcp_env_path = Path.home() / "Documents/Fintor/encompass-mcp-server/.env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path)
    print(f"✅ Loaded MCP server environment from {mcp_env_path}")

# Load local .env (won't override existing vars)
local_env_path = project_root / ".env"
if local_env_path.exists():
    load_dotenv(local_env_path, override=False)
    print(f"✅ Loaded local environment from {local_env_path}")

# IMPORTANT: Enable DRY RUN mode (no writes!)
os.environ["DRY_RUN"] = "true"

# Now import the verification agent
from agents.drawdocs.subagents.verification_agent.verification_agent import run_verification

def test_verification_agent():
    """Test the verification agent with primitives."""
    
    print("\n" + "="*80)
    print("TESTING VERIFICATION AGENT WITH PRIMITIVES")
    print("="*80)
    print("\nThis test will:")
    print("  1. Check loan preconditions")
    print("  2. Load prep output (17 extracted fields)")
    print("  3. Read current Encompass values for each field")
    print("  4. Compare prep vs Encompass values")
    print("  5. Identify mismatches (if any)")
    print("\n⚠️  DRY RUN MODE - NO WRITES TO ENCOMPASS")
    print("="*80)
    
    # Load the sample prep output
    prep_output_path = Path(__file__).parent / "data" / "prep_output.json"
    
    if not prep_output_path.exists():
        print(f"\n❌ Error: Sample prep output not found at {prep_output_path}")
        return None
    
    with open(prep_output_path, 'r') as f:
        prep_output = json.load(f)
    
    loan_id = prep_output.get("loan_id", "387596ee-7090-47ca-8385-206e22c9c9da")
    field_mappings = prep_output.get("results", {}).get("field_mappings", {})
    
    print(f"\nLoan ID: {loan_id}")
    print(f"Fields to verify: {len(field_mappings)}")
    
    if field_mappings:
        print(f"\nSample fields:")
        for i, (field_id, value) in enumerate(list(field_mappings.items())[:5], 1):
            print(f"  {i}. Field {field_id} = {value}")
    
    print("\n" + "="*80)
    print("Running Verification Agent...")
    print("="*80 + "\n")
    
    try:
        # Run verification in DRY RUN mode
        result = run_verification(
            loan_id=loan_id,
            prep_output=prep_output,
            dry_run=True  # IMPORTANT: No writes!
        )
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        
        # Check if result is dict or has messages
        if isinstance(result, dict):
            # Print status
            status = result.get("status", "N/A")
            print(f"\nStatus: {status}")
            
            # Print loan context if available
            loan_context = result.get("loan_context", {})
            if loan_context:
                print("\n--- Loan Context ---")
                print(f"Loan Number: {loan_context.get('loan_number', 'N/A')}")
                print(f"Loan Type: {loan_context.get('loan_type', 'N/A')}")
                print(f"State: {loan_context.get('state', 'N/A')}")
            
            # Print validation results if available
            validation_results = result.get("validation_results", [])
            if validation_results:
                print(f"\n--- Validation Results ---")
                print(f"Fields Validated: {len(validation_results)}")
                
                valid = sum(1 for r in validation_results if r.get("status") == "valid")
                invalid = sum(1 for r in validation_results if r.get("status") in ["invalid", "corrected"])
                
                print(f"Valid: {valid}")
                print(f"Invalid/Corrected: {invalid}")
            
            # Print corrections if any
            corrections = result.get("corrections_made", [])
            if corrections:
                print(f"\n--- Corrections (DRY RUN) ---")
                print(f"Total Corrections: {len(corrections)}")
                for i, corr in enumerate(corrections[:5], 1):
                    print(f"\n{i}. Field {corr.get('field_id')} - {corr.get('field_name', 'N/A')}")
                    print(f"   Corrected to: {corr.get('corrected_value')}")
                    print(f"   Reason: {corr.get('reason', 'N/A')}")
        
        # Save full results to file
        output_file = project_root / "verification_agent_test_output.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✅ Full results saved to: {output_file}")
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing verification agent: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n⚠️  READ-ONLY TEST - No changes will be made to Encompass")
    print("="*80)
    test_verification_agent()

