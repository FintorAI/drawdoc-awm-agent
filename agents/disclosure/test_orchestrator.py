"""Test script for Disclosure Orchestrator Agent (MVP).

Tests the orchestrator and individual sub-agents including:
- Verification with MVP eligibility check
- Preparation with MI calculation and tolerance checking
- Request with MI and tolerance in email
- Non-MVP case handling
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
        
        # Check MVP fields
        assert "is_mvp_supported" in results, "Missing is_mvp_supported"
        assert "handoff" in results, "Missing handoff data"
        
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
    """Test verification agent standalone with MVP eligibility."""
    print("\n" + "=" * 80)
    print("TEST: Verification Agent (MVP)")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.verification_agent.verification_agent import run_disclosure_verification
        
        result = run_disclosure_verification("387596ee-7090-47ca-8385-206e22c9c9da")
        
        assert result["status"] == "success", "Verification should succeed"
        assert "fields_checked" in result, "Missing fields_checked"
        assert "fields_missing" in result, "Missing fields_missing"
        assert "is_mvp_supported" in result, "Missing is_mvp_supported"
        assert "loan_type" in result, "Missing loan_type"
        assert "property_state" in result, "Missing property_state"
        
        print(f"  ✓ Fields checked: {result['fields_checked']}")
        print(f"  ✓ Fields missing: {len(result['fields_missing'])}")
        print(f"  ✓ MVP Supported: {result['is_mvp_supported']}")
        print(f"  ✓ Loan Type: {result.get('loan_type', 'Unknown')}")
        print(f"  ✓ State: {result.get('property_state', 'Unknown')}")
        
        print("\n✓ TEST PASSED: Verification agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_preparation_agent():
    """Test preparation agent standalone with MI calculation."""
    print("\n" + "=" * 80)
    print("TEST: Preparation Agent (MVP)")
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
        assert "mi_result" in result, "Missing mi_result"
        assert "tolerance_result" in result, "Missing tolerance_result"
        
        print(f"  ✓ Fields populated: {len(result['fields_populated'])}")
        print(f"  ✓ Fields cleaned: {len(result['fields_cleaned'])}")
        
        # MI result
        if result.get("mi_result"):
            mi = result["mi_result"]
            print(f"  ✓ MI Requires: {mi.get('requires_mi', 'N/A')}")
            if mi.get('requires_mi'):
                print(f"  ✓ MI Monthly: ${mi.get('monthly_amount', 0):.2f}")
        else:
            print(f"  ✓ MI Result: Not calculated")
        
        # Tolerance result
        if result.get("tolerance_result"):
            tol = result["tolerance_result"]
            print(f"  ✓ Tolerance Violations: {tol.get('has_violations', False)}")
        else:
            print(f"  ✓ Tolerance Result: Not checked")
        
        print("\n✓ TEST PASSED: Preparation agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_request_agent():
    """Test request agent standalone with MI and tolerance info."""
    print("\n" + "=" * 80)
    print("TEST: Request Agent (MVP)")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.request_agent.request_agent import run_disclosure_request
        
        # Mock verification and preparation results with MVP fields
        verification_results = {
            "fields_checked": 20,
            "fields_missing": ["FIELD1"],
            "fields_with_values": ["FIELD2", "FIELD3"],
            "is_mvp_supported": True,
            "mvp_warnings": [],
            "loan_type": "Conventional",
            "property_state": "NV"
        }
        
        preparation_results = {
            "fields_populated": ["FIELD1"],
            "fields_cleaned": ["FIELD2"],
            "fields_failed": [],
            "mi_result": {
                "requires_mi": True,
                "monthly_amount": 125.50,
                "source": "calculated",
                "ltv": 85.0
            },
            "tolerance_result": {
                "has_violations": False,
                "total_cure_needed": 0
            }
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
        assert "email_summary" in result, "Missing email_summary"
        
        summary = result.get("email_summary", {})
        print(f"  ✓ Email sent (dry run): {result['email_sent']}")
        print(f"  ✓ MI included: {summary.get('requires_mi', 'N/A')}")
        print(f"  ✓ Tolerance included: {not summary.get('has_tolerance_violations', True)}")
        
        print("\n✓ TEST PASSED: Request agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mi_calculator():
    """Test MI calculator directly."""
    print("\n" + "=" * 80)
    print("TEST: MI Calculator")
    print("=" * 80)
    
    try:
        from packages.shared import calculate_conventional_mi, calculate_mi
        
        # Test Conventional MI with LTV > 80%
        result = calculate_conventional_mi(
            loan_amount=400000,
            appraised_value=450000,  # ~89% LTV
            ltv=88.89,
        )
        
        assert result.requires_mi == True, "MI should be required for LTV > 80%"
        assert result.loan_type == "Conventional", "Loan type should be Conventional"
        assert result.monthly_amount > 0, "Monthly amount should be positive"
        assert result.cancel_at_ltv == 78.0, "Cancel at LTV should be 78%"
        
        print(f"  ✓ Requires MI: {result.requires_mi}")
        print(f"  ✓ LTV: {result.ltv:.2f}%")
        print(f"  ✓ Monthly Amount: ${result.monthly_amount:.2f}")
        print(f"  ✓ Cancel at LTV: {result.cancel_at_ltv}%")
        
        # Test Conventional MI with LTV <= 80%
        result2 = calculate_conventional_mi(
            loan_amount=350000,
            appraised_value=500000,  # 70% LTV
            ltv=70.0,
        )
        
        assert result2.requires_mi == False, "MI should not be required for LTV <= 80%"
        print(f"  ✓ No MI for LTV <= 80%: {not result2.requires_mi}")
        
        print("\n✓ TEST PASSED: MI calculator working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fee_tolerance():
    """Test fee tolerance calculator directly."""
    print("\n" + "=" * 80)
    print("TEST: Fee Tolerance Calculator")
    print("=" * 80)
    
    try:
        from packages.shared import check_fee_tolerance
        
        # Test with no violations
        result = check_fee_tolerance(
            le_fees={"NEWHUD.X7": 1000, "NEWHUD.X12": 500},
            cd_fees={"NEWHUD.X7": 1000, "NEWHUD.X12": 500}
        )
        
        assert result.has_violations == False, "Should have no violations with same fees"
        print(f"  ✓ No violations when fees match: {not result.has_violations}")
        
        # Test with 0% tolerance violation
        result2 = check_fee_tolerance(
            le_fees={"NEWHUD.X7": 1000, "NEWHUD.X12": 500},
            cd_fees={"NEWHUD.X7": 1100, "NEWHUD.X12": 500}  # $100 increase in origination
        )
        
        assert result2.has_violations == True, "Should have violation for Section A increase"
        assert len(result2.zero_tolerance_violations) > 0, "Should have zero tolerance violation"
        print(f"  ✓ Zero tolerance violation detected: {result2.has_violations}")
        print(f"  ✓ Cure needed: ${result2.total_cure_needed:.2f}")
        
        print("\n✓ TEST PASSED: Fee tolerance calculator working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_non_mvp_handling():
    """Test non-MVP loan handling."""
    print("\n" + "=" * 80)
    print("TEST: Non-MVP Loan Handling")
    print("=" * 80)
    
    try:
        from packages.shared import LoanType, PropertyState
        
        # Test loan type eligibility
        assert LoanType.is_mvp_supported("Conventional") == True, "Conventional should be MVP"
        assert LoanType.is_mvp_supported("FHA") == False, "FHA should not be MVP"
        assert LoanType.is_mvp_supported("VA") == False, "VA should not be MVP"
        assert LoanType.is_mvp_supported("USDA") == False, "USDA should not be MVP"
        
        print(f"  ✓ Conventional is MVP: True")
        print(f"  ✓ FHA is MVP: False")
        print(f"  ✓ VA is MVP: False")
        print(f"  ✓ USDA is MVP: False")
        
        # Test state eligibility
        assert PropertyState.is_mvp_supported("NV") == True, "NV should be MVP"
        assert PropertyState.is_mvp_supported("CA") == True, "CA should be MVP"
        assert PropertyState.is_mvp_supported("TX") == False, "TX should not be MVP"
        assert PropertyState.is_mvp_supported("FL") == False, "FL should not be MVP"
        
        print(f"  ✓ NV is MVP: True")
        print(f"  ✓ CA is MVP: True")
        print(f"  ✓ TX is MVP: False")
        print(f"  ✓ FL is MVP: False")
        
        print("\n✓ TEST PASSED: Non-MVP handling working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_handoff_schema():
    """Test handoff schema."""
    print("\n" + "=" * 80)
    print("TEST: Handoff Schema")
    print("=" * 80)
    
    try:
        from packages.shared import DisclosureHandoff, create_handoff_from_results
        from datetime import date
        
        # Test creating handoff from results
        verification_results = {
            "fields_checked": 20,
            "fields_missing": ["FIELD1"],
            "is_mvp_supported": True,
            "mvp_warnings": [],
            "loan_type": "Conventional",
            "property_state": "NV"
        }
        
        preparation_results = {
            "fields_populated": [],
            "fields_cleaned": [],
            "mi_result": {
                "requires_mi": True,
                "monthly_amount": 125.50
            },
            "tolerance_result": {
                "has_violations": False,
                "total_cure_needed": 0
            }
        }
        
        handoff = create_handoff_from_results(
            loan_id="test-loan-123",
            verification_results=verification_results,
            preparation_results=preparation_results,
        )
        
        assert handoff.loan_id == "test-loan-123", "Loan ID mismatch"
        assert handoff.is_mvp_supported == True, "MVP supported mismatch"
        assert handoff.loan_type == "Conventional", "Loan type mismatch"
        assert handoff.mi_calculated is not None, "MI should be included"
        
        print(f"  ✓ Loan ID: {handoff.loan_id}")
        print(f"  ✓ MVP Supported: {handoff.is_mvp_supported}")
        print(f"  ✓ Loan Type: {handoff.loan_type}")
        print(f"  ✓ State: {handoff.property_state}")
        print(f"  ✓ Requires Manual: {handoff.requires_manual}")
        
        # Test to_dict
        handoff_dict = handoff.to_dict()
        assert "loan_id" in handoff_dict, "to_dict should include loan_id"
        assert "mi_calculated" in handoff_dict, "to_dict should include mi_calculated"
        
        print(f"  ✓ to_dict works correctly")
        
        # Test summary
        summary = handoff.get_status_summary()
        assert "Conventional" in summary, "Summary should include loan type"
        print(f"  ✓ get_status_summary works correctly")
        
        print("\n✓ TEST PASSED: Handoff schema working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("=" * 80)
    print("DISCLOSURE AGENT TEST SUITE (MVP)")
    print("=" * 80)
    
    tests = [
        ("MI Calculator", test_mi_calculator),
        ("Fee Tolerance Calculator", test_fee_tolerance),
        ("Non-MVP Handling", test_non_mvp_handling),
        ("Handoff Schema", test_handoff_schema),
        ("Verification Agent", test_verification_agent),
        ("Preparation Agent", test_preparation_agent),
        ("Request Agent", test_request_agent),
        ("Orchestrator (Integration)", test_disclosure_orchestrator),
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
    
    passed_count = 0
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
        if passed:
            passed_count += 1
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed_count}/{len(results)} tests passed")
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
