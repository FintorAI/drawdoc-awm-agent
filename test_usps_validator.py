"""Test script for USPS Address Validator.

Tests the USPS Address API v3 integration with various address scenarios.
"""

import os
import sys
import json
from pathlib import Path
from dataclasses import asdict
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env")

from packages.shared.usps_validator import USPSAddressValidator, validate_address_sync


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(result):
    """Pretty print validation result."""
    # Convert dataclass to dict if needed
    if hasattr(result, '__dataclass_fields__'):
        result = asdict(result)
    print(json.dumps(result, indent=2))


def test_valid_address():
    """Test with a valid, complete address."""
    print_section("TEST 1: Valid Complete Address")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("❌ USPS validator is disabled - check USPS_CLIENT_ID and USPS_CLIENT_SECRET in .env")
        return False
    
    print("Testing address: 8345 W Sunset Rd Suite 380, Las Vegas, NV 89113")
    
    result = validator.validate_address(
        street_address="8345 W Sunset Rd",
        secondary_address="Suite 380",
        city="Las Vegas",
        state="NV",
        zip_code="89113"
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Address validated successfully!")
        print(f"   DPV Confirmation: {result.dpv_confirmation}")
        print(f"   Business: {result.business}")
        print(f"   Vacant: {result.vacant}")
        return True
    else:
        print(f"❌ Validation failed: {result.error}")
        return False


def test_address_without_secondary():
    """Test with address without suite/apt number."""
    print_section("TEST 2: Address Without Secondary Unit")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("⏭️  Skipping - validator disabled")
        return None
    
    print("Testing address: 8345 W Sunset Rd, Las Vegas, NV 89113")
    
    result = validator.validate_address(
        street_address="8345 W Sunset Rd",
        city="Las Vegas",
        state="NV",
        zip_code="89113"
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Address validated!")
        dpv = result.dpv_confirmation
        if dpv == 'D':
            print("   ⚠️  DPV='D': Primary confirmed, but secondary unit missing")
        elif dpv == 'Y':
            print("   ✓ DPV='Y': Fully confirmed")
        return True
    else:
        print(f"❌ Validation failed: {result.error}")
        return False


def test_address_with_zip_only():
    """Test with ZIP code but no city (city should be inferred)."""
    print_section("TEST 3: Address with ZIP Only (No City)")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("⏭️  Skipping - validator disabled")
        return None
    
    print("Testing address: 8345 W Sunset Rd, NV 89113 (no city)")
    
    result = validator.validate_address(
        street_address="8345 W Sunset Rd",
        state="NV",
        zip_code="89113"
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Address validated!")
        std = result.standardized_address
        if std:
            print(f"   City inferred: {std.get('city')}")
        return True
    else:
        print(f"❌ Validation failed: {result.error}")
        return False


def test_invalid_address():
    """Test with an invalid/non-existent address."""
    print_section("TEST 4: Invalid Address")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("⏭️  Skipping - validator disabled")
        return None
    
    print("Testing address: 99999 Nonexistent St, Las Vegas, NV 89999")
    
    result = validator.validate_address(
        street_address="99999 Nonexistent St",
        city="Las Vegas",
        state="NV",
        zip_code="89999"
    )
    
    print_result(result)
    
    if not result.success:
        print("✅ Correctly identified as invalid!")
        print(f"   Error: {result.error}")
        return True
    else:
        print("⚠️  Unexpectedly validated - should be invalid")
        return False


def test_address_with_corrections():
    """Test with address that needs standardization."""
    print_section("TEST 5: Address Requiring Standardization")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("⏭️  Skipping - validator disabled")
        return None
    
    print("Testing address: 8345 West Sunset Road #380, Las Vegas, Nevada 89113")
    print("(Using full words instead of abbreviations)")
    
    result = validator.validate_address(
        street_address="8345 West Sunset Road",
        secondary_address="#380",
        city="Las Vegas",
        state="NV",  # API expects 2-letter code
        zip_code="89113"
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Address validated and standardized!")
        std = result.standardized_address
        if std:
            print(f"   Original: 8345 West Sunset Road #380")
            print(f"   Standardized: {std.get('street')} {std.get('secondary')}")
        
        if result.warnings:
            print(f"   Warnings: {result.warnings}")
        return True
    else:
        print(f"❌ Validation failed: {result.error}")
        return False


def test_sync_wrapper():
    """Test the synchronous wrapper function."""
    print_section("TEST 6: Synchronous Wrapper Function")
    
    print("Testing validate_address_sync() wrapper...")
    
    result = validate_address_sync(
        street_address="8345 W Sunset Rd",
        city="Las Vegas",
        state="NV",
        zip_code="89113"
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Sync wrapper works correctly!")
        return True
    elif result.error and "credentials" in result.error.lower():
        print("ℹ️  Validator disabled (expected if no credentials)")
        return None
    else:
        print(f"❌ Sync wrapper failed: {result.error}")
        return False


def test_subject_property_scenario():
    """Test a real-world subject property validation scenario."""
    print_section("TEST 7: Subject Property Validation Scenario")
    
    validator = USPSAddressValidator()
    
    if not validator.enabled:
        print("⏭️  Skipping - validator disabled")
        return None
    
    # Simulate data from Encompass loan fields
    loan_data = {
        "subject_street": "8345 W Sunset Rd",
        "subject_city": "Las Vegas",
        "subject_state": "NV",
        "subject_zip": "89113"
    }
    
    print("Validating subject property from loan data:")
    print(f"  Address: {loan_data['subject_street']}")
    print(f"  City: {loan_data['subject_city']}")
    print(f"  State: {loan_data['subject_state']}")
    print(f"  ZIP: {loan_data['subject_zip']}")
    
    result = validator.validate_address(
        street_address=loan_data["subject_street"],
        city=loan_data["subject_city"],
        state=loan_data["subject_state"],
        zip_code=loan_data["subject_zip"]
    )
    
    print_result(result)
    
    if result.success:
        print("✅ Subject property address is valid!")
        
        # Check if address needs updating
        original = f"{loan_data['subject_street']}, {loan_data['subject_city']}, {loan_data['subject_state']} {loan_data['subject_zip']}"
        std = result.standardized_address
        if std:
            standardized = f"{std.get('street')}, {std.get('city')}, {std.get('state')} {std.get('zip_code')}"
            
            if original.upper() != standardized.upper():
                print("   ⚠️  Address differs from USPS standard:")
                print(f"      Original: {original}")
                print(f"      Standard: {standardized}")
                print("      Consider updating Encompass with standardized version")
            else:
                print("   ✓ Address matches USPS standard - no update needed")
        
        return True
    else:
        print(f"❌ Subject property address validation failed: {result.error}")
        return False


def main():
    """Run all USPS validator tests."""
    print("\n" + "🏛️  " * 20)
    print("USPS ADDRESS VALIDATOR TEST SUITE")
    print("🏛️  " * 20)
    
    # Check environment variables
    print("\n📋 Environment Check:")
    client_id = os.getenv("USPS_CLIENT_ID")
    client_secret = os.getenv("USPS_CLIENT_SECRET")
    
    if client_id and client_secret:
        print(f"✅ USPS_CLIENT_ID: {client_id[:10]}...{client_id[-4:]}")
        print(f"✅ USPS_CLIENT_SECRET: {client_secret[:10]}...{client_secret[-4:]}")
    else:
        print("❌ USPS credentials not found in .env file")
        print("   Add USPS_CLIENT_ID and USPS_CLIENT_SECRET to .env")
        print("   Tests will demonstrate graceful error handling")
    
    # Run tests
    tests = [
        ("Valid Complete Address", test_valid_address),
        ("Address Without Secondary", test_address_without_secondary),
        ("Address with ZIP Only", test_address_with_zip_only),
        ("Invalid Address", test_invalid_address),
        ("Address Requiring Standardization", test_address_with_corrections),
        ("Synchronous Wrapper", test_sync_wrapper),
        ("Subject Property Scenario", test_subject_property_scenario),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Print summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⏭️  SKIPPED"
        
        print(f"{status}: {test_name}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed, {skipped} skipped out of {total} tests")
    
    if failed > 0:
        print("\n⚠️  Some tests failed - review output above for details")
        return 1
    elif passed > 0:
        print("\n🎉 All enabled tests passed!")
        return 0
    else:
        print("\nℹ️  No tests were run - check USPS credentials in .env")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
