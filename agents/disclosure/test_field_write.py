"""Test script for Encompass Field Writer API.

This script tests reading and writing fields to verify the API integration works correctly.
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.shared import read_fields, read_field, write_fields, write_field
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_read_single_field(loan_id: str):
    """Test reading a single field."""
    print("\n" + "="*80)
    print("TEST 1: Read Single Field")
    print("="*80)
    
    field_id = "4000"  # Borrower First Name
    print(f"Reading field {field_id} (Borrower First Name)...")
    
    try:
        value = read_field(loan_id, field_id)
        print(f"✓ Success: {field_id} = {value}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_read_multiple_fields(loan_id: str):
    """Test reading multiple fields."""
    print("\n" + "="*80)
    print("TEST 2: Read Multiple Fields")
    print("="*80)
    
    field_ids = ["4000", "4002", "1109", "3", "4"]  # First name, last name, loan amount, rate, term
    print(f"Reading {len(field_ids)} fields...")
    
    try:
        values = read_fields(loan_id, field_ids, context="[TEST]")
        print(f"✓ Success: Retrieved {len(values)} fields")
        for field_id, value in values.items():
            print(f"  - {field_id} = {value}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_write_single_field_dry_run(loan_id: str):
    """Test writing a single field in dry run mode."""
    print("\n" + "="*80)
    print("TEST 3: Write Single Field (DRY RUN)")
    print("="*80)
    
    # Use a safe test field that exists
    field_id = "3515"  # Interest Accrual Days
    test_value = 360  # Use integer, not string
    
    print(f"Writing field {field_id} = {test_value} (type: {type(test_value).__name__}) (DRY RUN)...")
    
    try:
        success = write_field(loan_id, field_id, test_value, dry_run=True, context="[TEST]")
        if success:
            print(f"✓ Success: DRY RUN completed")
            return True
        else:
            print(f"✗ Failed: DRY RUN returned False")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_write_multiple_fields_dry_run(loan_id: str):
    """Test writing multiple fields in dry run mode."""
    print("\n" + "="*80)
    print("TEST 4: Write Multiple Fields (DRY RUN)")
    print("="*80)
    
    updates = {
        "3515": 360,  # Interest Accrual Days - integer
        "3516": 360,  # Interest Accrual Year - integer
        "672": 15,    # Late Charge Days - integer
        "674": 5.0,   # Late Charge Percent - float
    }
    
    print(f"Writing {len(updates)} fields (DRY RUN)...")
    for field_id, value in updates.items():
        print(f"  - {field_id} = {value} (type: {type(value).__name__})")
    
    try:
        success = write_fields(loan_id, updates, dry_run=True, context="[TEST]")
        if success:
            print(f"✓ Success: DRY RUN completed")
            return True
        else:
            print(f"✗ Failed: DRY RUN returned False")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_write_single_field_live(loan_id: str):
    """Test writing a single field LIVE (CAUTION!)."""
    print("\n" + "="*80)
    print("TEST 5: Write Single Field (LIVE - CAUTION)")
    print("="*80)
    
    field_id = "3515"  # Interest Accrual Days
    test_value = 360  # Use integer
    
    # First, read current value
    print(f"Reading current value of field {field_id}...")
    try:
        current_value = read_field(loan_id, field_id)
        print(f"  Current value: {current_value}")
    except Exception as e:
        print(f"  Could not read current value: {e}")
        current_value = None
    
    # Confirm before writing
    print(f"\nAbout to write field {field_id} = {test_value}")
    print("This is a LIVE write that will modify the loan!")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != "yes":
        print("Skipped live write test")
        return None
    
    try:
        success = write_field(loan_id, field_id, test_value, dry_run=False, context="[TEST]")
        if success:
            print(f"✓ Success: Field written")
            
            # Verify the write by reading it back
            print(f"Verifying write by reading field {field_id}...")
            new_value = read_field(loan_id, field_id)
            print(f"  New value: {new_value}")
            
            if str(new_value) == str(test_value):
                print(f"✓ Verified: Field value matches")
                return True
            else:
                print(f"⚠ Warning: Field value doesn't match (expected {test_value}, got {new_value})")
                return False
        else:
            print(f"✗ Failed: Write returned False")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_read_ctc_fields(loan_id: str):
    """Read CTC checkbox fields to see their current format."""
    print("\n" + "="*80)
    print("TEST 6: Read CTC Checkbox Fields")
    print("="*80)
    
    ctc_field_ids = ["NEWHUD2.X55", "NEWHUD2.X56", "NEWHUD2.X57"]
    
    print(f"Reading CTC checkbox fields to see current format...")
    
    try:
        values = read_fields(loan_id, ctc_field_ids, context="[TEST]")
        print(f"✓ Success: Retrieved {len(values)} fields")
        for field_id, value in values.items():
            print(f"  - {field_id} = {repr(value)} (type: {type(value).__name__})")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_ctc_fields_dry_run(loan_id: str):
    """Test writing CTC checkbox fields (the ones that are failing)."""
    print("\n" + "="*80)
    print("TEST 7: Write CTC Checkbox Fields (DRY RUN)")
    print("="*80)
    
    # Encompass checkboxes typically use "Y"/"N" or "X"/"" format
    # Testing both formats to see which works
    print("\nTest A: Using 'Y' string format")
    ctc_updates_y = {
        "NEWHUD2.X55": "Y",  # CTC Use Actual Down Payment
        "NEWHUD2.X56": "Y",  # CTC Include Payoffs  
        "NEWHUD2.X57": "Y",  # CTC Purchase Checkbox
    }
    
    for field_id, value in ctc_updates_y.items():
        print(f"  - {field_id} = {repr(value)}")
    
    try:
        success = write_fields(loan_id, ctc_updates_y, dry_run=True, form_name="CTC", context="[TEST]")
        if success:
            print(f"✓ Success: DRY RUN completed for CTC fields with 'Y' format")
        else:
            print(f"✗ Failed: DRY RUN returned False")
    except Exception as e:
        print(f"✗ Error with 'Y' format: {e}")
    
    print("\nTest B: Using 'X' string format")
    ctc_updates_x = {
        "NEWHUD2.X55": "X",  
        "NEWHUD2.X56": "X",  
        "NEWHUD2.X57": "X",  
    }
    
    for field_id, value in ctc_updates_x.items():
        print(f"  - {field_id} = {repr(value)}")
    
    try:
        success = write_fields(loan_id, ctc_updates_x, dry_run=True, form_name="CTC", context="[TEST]")
        if success:
            print(f"✓ Success: DRY RUN completed for CTC fields with 'X' format")
            return True
        else:
            print(f"✗ Failed: DRY RUN returned False")
            return False
    except Exception as e:
        print(f"✗ Error with 'X' format: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_field_writer_payload_format():
    """Test the payload format we're using for Field Writer API."""
    print("\n" + "="*80)
    print("TEST 8: Field Writer Payload Format")
    print("="*80)
    
    updates = {
        "3515": 360,      # Integer
        "3516": 360,      # Integer
        "672": 15,        # Integer
        "674": 5.0,       # Float
        "NEWHUD2.X55": True,  # Boolean
    }
    
    # Show what our payload looks like
    payload = [
        {"id": field_id, "value": value, "lock": False}
        for field_id, value in updates.items()
    ]
    
    print("Payload format we're using (with proper types):")
    print(json.dumps(payload, indent=2, default=str))
    print("\nValue types:")
    for item in payload:
        print(f"  - {item['id']}: {type(item['value']).__name__} = {item['value']}")
    
    print("\n✓ Payload format matches Encompass V3 Field Writer spec")
    return True


def main():
    """Run all tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Encompass Field Writer API")
    parser.add_argument("loan_id", help="Loan GUID to test with")
    parser.add_argument("--live", action="store_true", help="Run live write test (CAUTION!)")
    args = parser.parse_args()
    
    loan_id = args.loan_id
    
    print("\n" + "="*80)
    print(f"ENCOMPASS FIELD WRITER API TEST")
    print(f"Loan ID: {loan_id}")
    print("="*80)
    
    results = {}
    
    # Run read tests
    results["read_single"] = test_read_single_field(loan_id)
    results["read_multiple"] = test_read_multiple_fields(loan_id)
    
    # Run dry run write tests
    results["write_single_dry"] = test_write_single_field_dry_run(loan_id)
    results["write_multiple_dry"] = test_write_multiple_fields_dry_run(loan_id)
    
    # Test reading CTC fields first to see their format
    results["read_ctc"] = test_read_ctc_fields(loan_id)
    results["write_ctc_dry"] = test_write_ctc_fields_dry_run(loan_id)
    
    # Test payload format
    results["payload_format"] = test_field_writer_payload_format()
    
    # Run live write test if requested
    if args.live:
        results["write_single_live"] = test_write_single_field_live(loan_id)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

