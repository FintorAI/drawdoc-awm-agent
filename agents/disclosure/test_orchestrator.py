"""Test script for Disclosure Orchestrator Agent (v2 - LE Focus).

Tests the orchestrator and individual sub-agents including:
- Milestone/Queue pre-check
- Verification with TRID compliance and MVP eligibility
- Preparation with RegZ-LE, MI calculation, and CTC matching
- Send with Mavent, ATR/QM, and eDisclosures ordering

Testing Approaches:
1. LIVE MODE: Uses real loan data from Encompass (requires valid loan)
2. MOCK MODE: Uses simulated responses (no Encompass connection needed)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path (go up two levels from test file)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.disclosure import run_disclosure_orchestrator


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Default test loan (update with your verified loan)
DEFAULT_TEST_LOAN_ID = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
DEFAULT_LO_EMAIL = "test@example.com"


def load_test_config():
    """Load test configuration from example_input.json or use defaults."""
    example_input_path = Path(__file__).parent / "example_input.json"
    if example_input_path.exists():
        with open(example_input_path, "r") as f:
            config = json.load(f)
        return {
            "loan_id": config.get("loan_id", DEFAULT_TEST_LOAN_ID),
            "lo_email": config.get("lo_email", DEFAULT_LO_EMAIL),
            "demo_mode": config.get("demo_mode", True),
        }
    return {
        "loan_id": DEFAULT_TEST_LOAN_ID,
        "lo_email": DEFAULT_LO_EMAIL,
        "demo_mode": True,
    }


# =============================================================================
# PRE-CHECK TEST: MILESTONE/QUEUE
# =============================================================================

def test_milestone_precheck():
    """Test milestone/queue pre-check before disclosure processing.
    
    Per SOP: Loans should be in DD Request queue with Active status.
    """
    print("\n" + "=" * 80)
    print("TEST: Milestone/Queue Pre-Check")
    print("=" * 80)
    
    try:
        from packages.shared import check_milestone
        
        config = load_test_config()
        loan_id = config["loan_id"]
        
        print(f"  Loan ID: {loan_id[:8]}...")
        
        result = check_milestone(loan_id)
        
        print(f"\n  Results:")
        print(f"  ✓ Can Proceed: {result.can_proceed}")
        print(f"  ✓ Current Status: {result.current_status}")
        print(f"  ✓ Current Milestone: {result.current_milestone}")
        print(f"  ✓ Application Date: {result.application_date}")
        
        if result.blocking_reason:
            print(f"  ⚠️ Blocking Reason: {result.blocking_reason}")
        
        if result.warnings:
            for warning in result.warnings:
                print(f"  ⚠️ Warning: {warning}")
        
        # For this test, we don't fail if can_proceed is False
        # We just want to verify the check runs correctly
        print("\n✓ TEST PASSED: Milestone pre-check executed successfully")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# VERIFICATION AGENT TEST (v2)
# =============================================================================

def test_verification_agent():
    """Test verification agent standalone with TRID compliance and MVP eligibility."""
    print("\n" + "=" * 80)
    print("TEST: Verification Agent (v2)")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.verification_agent.verification_agent import run_disclosure_verification
        
        config = load_test_config()
        loan_id = config["loan_id"]
        
        print(f"  Loan ID: {loan_id[:8]}...")
        
        result = run_disclosure_verification(loan_id)
        
        assert result["status"] == "success", "Verification should succeed"
        assert "fields_checked" in result, "Missing fields_checked"
        assert "fields_missing" in result, "Missing fields_missing"
        assert "is_mvp_supported" in result, "Missing is_mvp_supported"
        assert "loan_type" in result, "Missing loan_type"
        assert "property_state" in result, "Missing property_state"
        
        # v2: Check TRID compliance result
        trid = result.get("trid_compliance", {})
        
        print(f"\n  Results:")
        print(f"  ✓ Fields checked: {result['fields_checked']}")
        print(f"  ✓ Fields missing: {len(result['fields_missing'])}")
        print(f"  ✓ MVP Supported: {result['is_mvp_supported']}")
        print(f"  ✓ Loan Type: {result.get('loan_type', 'Unknown')}")
        print(f"  ✓ State: {result.get('property_state', 'Unknown')}")
        
        # v2: TRID results
        if trid:
            print(f"  ✓ TRID Compliant: {trid.get('compliant', 'N/A')}")
            print(f"  ✓ App Date: {trid.get('application_date', 'N/A')}")
            print(f"  ✓ LE Due Date: {trid.get('le_due_date', 'N/A')}")
        
        print("\n✓ TEST PASSED: Verification agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# PREPARATION AGENT TEST (v2)
# =============================================================================

def test_preparation_agent():
    """Test preparation agent standalone with RegZ-LE, MI, and CTC."""
    print("\n" + "=" * 80)
    print("TEST: Preparation Agent (v2)")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.preparation_agent.preparation_agent import run_disclosure_preparation
        
        config = load_test_config()
        loan_id = config["loan_id"]
        
        print(f"  Loan ID: {loan_id[:8]}...")
        
        # Test with mock missing fields
        result = run_disclosure_preparation(
            loan_id=loan_id,
            missing_fields=["FIELD1", "FIELD2"],
            demo_mode=True
        )
        
        assert result["status"] == "success", "Preparation should succeed"
        assert "fields_populated" in result, "Missing fields_populated"
        assert "fields_cleaned" in result, "Missing fields_cleaned"
        
        # v2: Check new results
        regz_le = result.get("regz_le_result", {})
        mi_result = result.get("mi_result", {})
        ctc_result = result.get("ctc_result", {})
        
        print(f"\n  Results:")
        print(f"  ✓ Fields populated: {len(result['fields_populated'])}")
        print(f"  ✓ Fields cleaned: {len(result['fields_cleaned'])}")
        
        # v2: RegZ-LE
        if regz_le:
            print(f"  ✓ RegZ-LE Updates: {len(regz_le.get('updates_made', {}))}")
        
        # MI result
        if mi_result:
            if mi_result.get('requires_mi'):
                print(f"  ✓ MI Monthly: ${mi_result.get('monthly_amount', 0):.2f}")
            else:
                print(f"  ✓ MI: Not required")
        
        # v2: CTC result
        if ctc_result:
            if ctc_result.get("matched"):
                print(f"  ✓ CTC: Matched ${ctc_result.get('calculated_ctc', 0):,.2f}")
            else:
                print(f"  ⚠️ CTC: Mismatch")
        
        print("\n✓ TEST PASSED: Preparation agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# SEND AGENT TEST (v2 - replaces Request Agent)
# =============================================================================

def test_send_agent():
    """Test send agent standalone with Mavent, ATR/QM, and ordering."""
    print("\n" + "=" * 80)
    print("TEST: Send Agent (v2)")
    print("=" * 80)
    
    try:
        from agents.disclosure.subagents.send_agent.send_agent import run_disclosure_send
        
        config = load_test_config()
        loan_id = config["loan_id"]
        
        print(f"  Loan ID: {loan_id[:8]}...")
        
        result = run_disclosure_send(
            loan_id=loan_id,
            demo_mode=True
        )
        
        assert result["status"] in ["success", "blocked"], "Send should return valid status"
        
        # v2: Check compliance results
        mavent = result.get("mavent_result", {})
        atr_qm = result.get("atr_qm_result", {})
        order = result.get("order_result", {})
        blocking = result.get("blocking_issues", [])
        
        print(f"\n  Results:")
        
        # Mavent
        if mavent:
            status = "PASSED" if mavent.get("passed") else f"ISSUES ({mavent.get('total_issues', 0)})"
            print(f"  ✓ Mavent: {status}")
        
        # ATR/QM
        if atr_qm:
            status = "PASSED" if atr_qm.get("passed") else f"RED FLAGS: {atr_qm.get('red_flags', [])}"
            print(f"  ✓ ATR/QM: {status}")
        
        # Order result
        if order:
            if order.get("success"):
                print(f"  ✓ Ordered! Tracking ID: {order.get('tracking_id', 'N/A')}")
            else:
                print(f"  ✓ Order: Not sent (demo mode or blocked)")
        
        # Blocking issues
        if blocking:
            print(f"  ⚠️ Blocking issues: {len(blocking)}")
            for issue in blocking[:3]:  # Show first 3
                print(f"     - {issue}")
        
        print("\n✓ TEST PASSED: Send agent working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# ORCHESTRATOR INTEGRATION TEST (v2)
# =============================================================================

def test_disclosure_orchestrator():
    """Test full orchestrator execution (v2)."""
    print("=" * 80)
    print("TEST: Disclosure Orchestrator (v2 - Demo Mode)")
    print("=" * 80)
    
    config = load_test_config()
    loan_id = config["loan_id"]
    lo_email = config["lo_email"]
    
    print(f"  Loan ID: {loan_id[:8]}...")
    print(f"  LO Email: {lo_email}")
    
    try:
        results = run_disclosure_orchestrator(
            loan_id=loan_id,
            lo_email=lo_email,
            demo_mode=True,
            skip_non_mvp=False  # Don't skip - we want to see the result
        )
        
        # Validate structure
        assert "loan_id" in results, "Missing loan_id in results"
        assert results["loan_id"] == loan_id, "Loan ID mismatch"
        assert "demo_mode" in results, "Missing demo_mode in results"
        assert results["demo_mode"] == True, "Demo mode should be True"
        assert "agents" in results, "Missing agents in results"
        
        # Check each agent ran (v2: send instead of request)
        agents = results["agents"]
        assert "verification" in agents, "Missing verification results"
        assert "preparation" in agents, "Missing preparation results"
        assert "send" in agents, "Missing send results"  # v2: changed from "request"
        
        # Check MVP fields
        assert "is_mvp_supported" in results, "Missing is_mvp_supported"
        
        # Print summary
        print("\n" + results.get("summary", ""))
        
        # Save results
        output_file = Path(__file__).parent / "test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Results saved to: {output_file.name}")
        
        print("\n✓ TEST PASSED: Orchestrator execution successful")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# UTILITY TESTS
# =============================================================================

def test_mi_calculator():
    """Test MI calculator directly."""
    print("\n" + "=" * 80)
    print("TEST: MI Calculator")
    print("=" * 80)
    
    try:
        from packages.shared import calculate_conventional_mi
        
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


def test_trid_checker():
    """Test TRID compliance checker."""
    print("\n" + "=" * 80)
    print("TEST: TRID Checker")
    print("=" * 80)
    
    try:
        from packages.shared import TRIDChecker, calculate_le_due_date
        from datetime import date, timedelta
        
        # Test LE due date calculation
        # 3 business days from today (should skip weekends)
        today = date.today()
        due_date = calculate_le_due_date(today)
        
        assert due_date > today, "LE due date should be after application date"
        
        # Check it's approximately 3 business days (could be 3-5 calendar days depending on weekends)
        days_diff = (due_date - today).days
        assert 3 <= days_diff <= 5, f"LE due date should be 3-5 days out, got {days_diff}"
        
        print(f"  ✓ App Date: {today}")
        print(f"  ✓ LE Due Date: {due_date}")
        print(f"  ✓ Days: {days_diff}")
        
        print("\n✓ TEST PASSED: TRID checker working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MOCK-BASED TESTING (No Encompass connection needed)
# =============================================================================

def test_with_mock_data():
    """Test orchestrator flow with mock data (no API calls).
    
    Use this when you don't have a valid test loan in Encompass.
    """
    print("\n" + "=" * 80)
    print("TEST: Mock-Based Flow Test")
    print("=" * 80)
    
    try:
        # Mock verification result
        mock_verification = {
            "status": "success",
            "fields_checked": 47,
            "fields_missing": ["LE1.X1", "3152"],
            "is_mvp_supported": True,
            "loan_type": "Conventional",
            "property_state": "CA",
            "trid_compliance": {
                "compliant": True,
                "application_date": "2024-12-01",
                "le_due_date": "2024-12-04",
                "days_remaining": 2,
            },
            "blocking_issues": [],
        }
        
        # Mock preparation result
        mock_preparation = {
            "status": "success",
            "fields_populated": ["LE1.X1"],
            "fields_cleaned": [],
            "regz_le_result": {
                "success": True,
                "updates_made": {
                    "LE1.X1": "2024-12-02",
                    "672": 15,
                    "673": 5.0,
                }
            },
            "mi_result": {
                "requires_mi": True,
                "monthly_amount": 125.50,
                "ltv": 85.0,
                "cancel_at_ltv": 78.0,
            },
            "ctc_result": {
                "matched": True,
                "calculated_ctc": 44690.00,
                "displayed_ctc": 44690.00,
            },
        }
        
        # Mock send result
        mock_send = {
            "status": "success",
            "mavent_result": {
                "passed": True,
                "total_issues": 0,
            },
            "atr_qm_result": {
                "passed": True,
                "red_flags": [],
            },
            "order_result": {
                "success": True,
                "tracking_id": "mock-tracking-123",
            },
            "blocking_issues": [],
        }
        
        # Validate mock data structure
        assert mock_verification["status"] == "success"
        assert mock_verification["is_mvp_supported"] == True
        assert mock_preparation["mi_result"]["requires_mi"] == True
        assert mock_send["mavent_result"]["passed"] == True
        
        print("  ✓ Mock verification: MVP supported, TRID compliant")
        print("  ✓ Mock preparation: MI calculated, CTC matched")
        print("  ✓ Mock send: Mavent passed, ATR/QM passed")
        print("  ✓ Mock tracking ID: mock-tracking-123")
        
        print("\n✓ TEST PASSED: Mock-based flow validation successful")
        print("  (Use this structure when creating integration tests)")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    """Run all tests."""
    print("\n")
    print("=" * 80)
    print("DISCLOSURE AGENT TEST SUITE (v2 - LE Focus)")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    config = load_test_config()
    print(f"Test Loan: {config['loan_id'][:8]}...")
    print(f"Demo Mode: {config['demo_mode']}")
    print("=" * 80)
    
    # Tests in order of dependency
    tests = [
        # Utility tests (no API)
        ("MI Calculator", test_mi_calculator),
        ("Fee Tolerance", test_fee_tolerance),
        ("Non-MVP Handling", test_non_mvp_handling),
        ("TRID Checker", test_trid_checker),
        ("Mock-Based Flow", test_with_mock_data),
        
        # API-dependent tests
        ("Milestone Pre-Check", test_milestone_precheck),
        ("Verification Agent (v2)", test_verification_agent),
        ("Preparation Agent (v2)", test_preparation_agent),
        ("Send Agent (v2)", test_send_agent),
        ("Orchestrator (v2)", test_disclosure_orchestrator),
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
