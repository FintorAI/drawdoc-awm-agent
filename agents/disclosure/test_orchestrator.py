"""Test script for Disclosure Orchestrator Agent.

Tests the orchestrator and individual sub-agents.
"""

import sys
import json
from pathlib import Path

# Add project root to path (go up two levels from test file)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.disclosure import run_disclosure_orchestrator


def test_disclosure_orchestrator():
    """Test basic orchestrator execution in demo mode."""
    print("=" * 80)
    print("TEST: Disclosure Orchestrator (Demo Mode)")
    print("=" * 80)
    
    # Load example input
    example_input_path = Path(__file__).parent / "example_input.json"
    if example_input_path.exists():
        with open(example_input_path, "r") as f:
            config = json.load(f)
        loan_id = config.get("loan_id", "387596ee-7090-47ca-8385-206e22c9c9da")
        lo_email = config.get("lo_email", "test@example.com")
        print(f"  Loaded config from example_input.json")
    else:
        loan_id = "387596ee-7090-47ca-8385-206e22c9c9da"
        lo_email = "test@example.com"
    
    print(f"  Loan ID: {loan_id[:8]}...")
    print(f"  LO Email: {lo_email}")
    
    try:
        results = run_disclosure_orchestrator(
            loan_id=loan_id,
            lo_email=lo_email,
            demo_mode=True
        )
        
        # Validate structure
        assert "loan_id" in results, "Missing loan_id in results"
        assert results["loan_id"] == loan_id, "Loan ID mismatch"
        assert "demo_mode" in results, "Missing demo_mode in results"
        assert results["demo_mode"] == True, "Demo mode should be True"
        assert "agents" in results, "Missing agents in results"
        
        # Check each agent ran
        agents = results["agents"]
        assert "verification" in agents, "Missing verification results"
        assert "preparation" in agents, "Missing preparation results"
        assert "request" in agents, "Missing request results"
        
        # Print summary
        print("\n" + results.get("summary", ""))
        
        # Save results
        output_file = Path(__file__).parent / "test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Results saved to: {output_file.name}")
        
        print("\n✓ TEST PASSED: Basic execution successful")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verification_agent():
    """Test verification agent standalone."""
    print("\n" + "=" * 80)
    print("TEST: Verification Agent")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.verification_agent.verification_agent import run_disclosure_verification
        
        result = run_disclosure_verification("387596ee-7090-47ca-8385-206e22c9c9da")
        
        assert result["status"] == "success", "Verification should succeed"
        assert "fields_checked" in result, "Missing fields_checked"
        assert "fields_missing" in result, "Missing fields_missing"
        
        print(f"  ✓ Fields checked: {result['fields_checked']}")
        print(f"  ✓ Fields missing: {len(result['fields_missing'])}")
        
        print("\n✓ TEST PASSED: Verification agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False


def test_preparation_agent():
    """Test preparation agent standalone."""
    print("\n" + "=" * 80)
    print("TEST: Preparation Agent")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.preparation_agent.preparation_agent import run_disclosure_preparation
        
        # Test with mock missing fields
        result = run_disclosure_preparation(
            loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
            missing_fields=["FIELD1", "FIELD2"],
            demo_mode=True
        )
        
        assert result["status"] == "success", "Preparation should succeed"
        assert "fields_populated" in result, "Missing fields_populated"
        assert "fields_cleaned" in result, "Missing fields_cleaned"
        
        print(f"  ✓ Fields populated: {len(result['fields_populated'])}")
        print(f"  ✓ Fields cleaned: {len(result['fields_cleaned'])}")
        
        print("\n✓ TEST PASSED: Preparation agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False


def test_request_agent():
    """Test request agent standalone."""
    print("\n" + "=" * 80)
    print("TEST: Request Agent")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.request_agent.request_agent import run_disclosure_request
        
        # Mock verification and preparation results
        verification_results = {
            "fields_checked": 50,
            "fields_missing": ["FIELD1"],
            "fields_with_values": []
        }
        
        preparation_results = {
            "fields_populated": ["FIELD1"],
            "fields_cleaned": ["FIELD2"],
            "fields_failed": []
        }
        
        result = run_disclosure_request(
            loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
            lo_email="test@example.com",
            verification_results=verification_results,
            preparation_results=preparation_results,
            demo_mode=True
        )
        
        assert result["status"] == "success", "Request should succeed"
        assert "email_sent" in result, "Missing email_sent"
        assert result["lo_email"] == "test@example.com", "LO email mismatch"
        
        print(f"  ✓ Email sent (dry run): {result['email_sent']}")
        
        print("\n✓ TEST PASSED: Request agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("=" * 80)
    print("DISCLOSURE AGENT TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Verification Agent", test_verification_agent),
        ("Preparation Agent", test_preparation_agent),
        ("Request Agent", test_request_agent),
        ("Orchestrator (Integration)", test_disclosure_orchestrator)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

