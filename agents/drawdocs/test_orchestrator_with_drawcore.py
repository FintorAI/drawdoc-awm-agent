#!/usr/bin/env python3
"""
Test script for Orchestrator with Drawcore Agent integration.
READ-ONLY MODE: No writes to Encompass.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
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

# Now import the orchestrator
from agents.drawdocs.orchestrator_agent import run_orchestrator

def test_orchestrator_with_drawcore():
    """Test the complete orchestrator with all 4 agents."""
    
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR WITH DRAWCORE AGENT")
    print("="*80)
    print("\nThis test will run the complete 4-agent pipeline:")
    print("  1. Prep Agent       → Extract fields from documents")
    print("  2. Drawcore Agent   → Update Encompass fields")
    print("  3. Verification     → Validate and correct")
    print("  4. Orderdocs Agent  → Check completeness")
    print("\n⚠️  DRY RUN MODE - NO WRITES TO ENCOMPASS")
    print("="*80)
    
    # Test with prep output (use existing prep data if available)
    prep_output_path = project_root / "agents/drawdocs/subagents/verification_agent/data/prep_output.json"
    
    if prep_output_path.exists():
        print(f"\n✅ Using existing prep output from: {prep_output_path}")
        with open(prep_output_path, 'r') as f:
            prep_data = json.load(f)
        loan_id = prep_data.get("loan_id", "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6")
        field_count = len(prep_data.get("results", {}).get("field_mappings", {}))
        print(f"   Loan ID: {loan_id}")
        print(f"   Extracted fields: {field_count}")
    else:
        print(f"\n⚠️  No existing prep output found")
        print(f"   Will run full pipeline starting with Prep Agent")
        loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("\n" + "="*80)
    print("Running Orchestrator...")
    print("="*80 + "\n")
    
    try:
        # Run orchestrator in DRY RUN mode
        result = run_orchestrator(
            loan_id=loan_id,
            demo_mode=True,  # IMPORTANT: No writes!
            output_file=str(project_root / "orchestrator_test_output.json")
        )
        
        print("\n" + "="*80)
        print("ORCHESTRATOR TEST COMPLETE")
        print("="*80)
        
        # Check results
        agents = result.get("agents", {})
        print(f"\nAgents executed: {len(agents)}")
        
        for agent_name, agent_result in agents.items():
            status = agent_result.get("status", "unknown")
            symbol = "✓" if status == "success" else "⚠" if status == "partial_success" else "✗"
            print(f"  {symbol} {agent_name.title()}: {status}")
        
        print(f"\nDetailed results saved to:")
        print(f"  - orchestrator_test_output.json")
        print(f"  - orchestrator_test_output_summary.txt")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n⚠️  READ-ONLY TEST - No changes will be made to Encompass")
    print("="*80)
    test_orchestrator_with_drawcore()

