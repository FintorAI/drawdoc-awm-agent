"""Test all 12 loan summary fields for a specific loan.

This script tests reading all fields used by get_loan_summary() to verify
Encompass connectivity and see which fields are available.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.shared import read_field, read_fields
from packages.shared.auth import get_access_token


# Field definitions from encompass_io.py
LOAN_SUMMARY_FIELDS = {
    "1172": "Loan Type (Conventional, FHA, VA, USDA)",
    "19": "Loan Purpose (Purchase, Refinance, etc.)",
    "1109": "Loan Amount",
    "356": "Appraised Value",
    "136": "Purchase Price",
    "1041": "Property Type",
    "1811": "Occupancy Type",
    "14": "Property State",
    "353": "LTV",
    "976": "CLTV",
    "3": "Interest Rate (Note Rate)",
    "4": "Loan Term (months)",
}


def check_credentials():
    """Check if Encompass credentials are configured.
    
    Supports two authentication methods:
    1. OAuth2 auto-generate: CLIENT_ID + CLIENT_SECRET + INSTANCE_ID
    2. Manual token: ACCESS_TOKEN
    """
    print("\n" + "=" * 80)
    print("CHECKING ENCOMPASS CREDENTIALS")
    print("=" * 80)
    
    # Check for OAuth2 credentials (preferred method)
    client_id = os.getenv("ENCOMPASS_CLIENT_ID")
    client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
    instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
    
    # Check for manual token (alternative method)
    access_token = os.getenv("ENCOMPASS_ACCESS_TOKEN")
    
    # Show what's available
    if client_id:
        preview = client_id[:10] + "..." if len(client_id) > 10 else client_id
        print(f"✓ ENCOMPASS_CLIENT_ID: {preview}")
    else:
        print(f"✗ ENCOMPASS_CLIENT_ID: NOT SET")
    
    if client_secret:
        preview = client_secret[:10] + "..." if len(client_secret) > 10 else client_secret
        print(f"✓ ENCOMPASS_CLIENT_SECRET: {preview}")
    else:
        print(f"✗ ENCOMPASS_CLIENT_SECRET: NOT SET")
    
    if instance_id:
        preview = instance_id[:10] + "..." if len(instance_id) > 10 else instance_id
        print(f"✓ ENCOMPASS_INSTANCE_ID: {preview}")
    else:
        print(f"✗ ENCOMPASS_INSTANCE_ID: NOT SET")
    
    if access_token:
        preview = access_token[:10] + "..." if len(access_token) > 10 else access_token
        print(f"✓ ENCOMPASS_ACCESS_TOKEN: {preview} (manual token)")
    else:
        print(f"  ENCOMPASS_ACCESS_TOKEN: NOT SET (will auto-generate)")
    
    print()
    
    # Determine which authentication method to use
    has_oauth_creds = all([client_id, client_secret, instance_id])
    has_manual_token = bool(access_token)
    
    if has_oauth_creds:
        print("✅ OAuth2 credentials found - will auto-generate token")
        return True
    elif has_manual_token:
        print("✅ Manual access token found")
        return True
    else:
        print("❌ No valid authentication method found")
        print("\nYou need EITHER:")
        print("\nOption 1 (Recommended): OAuth2 Client Credentials")
        print("   ENCOMPASS_CLIENT_ID=your_client_id")
        print("   ENCOMPASS_CLIENT_SECRET=your_client_secret")
        print("   ENCOMPASS_INSTANCE_ID=your_instance_id")
        print("\nOption 2: Manual Access Token")
        print("   ENCOMPASS_ACCESS_TOKEN=your_pre_generated_token")
        print("\nAdd these to your .env file in the project root")
        return False


def test_all_fields(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"):
    """Test reading all 12 loan summary fields.
    
    Args:
        loan_id: Encompass loan GUID
    """
    print("\n" + "=" * 80)
    print("TESTING ALL LOAN SUMMARY FIELDS")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    print(f"Fields to test: {len(LOAN_SUMMARY_FIELDS)}")
    
    # Check credentials first
    has_creds = check_credentials()
    
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Try to generate OAuth2 token if using that method
    if not os.getenv("ENCOMPASS_ACCESS_TOKEN"):
        print("\n" + "-" * 80)
        print("GENERATING OAUTH2 TOKEN")
        print("-" * 80)
        print()
        
        try:
            token = get_access_token()
            print("✅ OAuth2 token generated successfully!")
            print(f"   Token: {token[:20]}...{token[-10:]}")
            print(f"   Length: {len(token)} characters")
            print()
        except Exception as e:
            print(f"❌ Failed to generate OAuth2 token: {e}")
            print("\nPossible issues:")
            print("  - Invalid client_id or client_secret")
            print("  - Instance_id doesn't match credentials")
            print("  - Network connectivity issues")
            print("  - Encompass API endpoint unreachable")
            print("\nPlease verify your credentials in .env file")
            return None
    
    # Test 1: Try reading all fields at once (batch read)
    print("\n" + "-" * 80)
    print("TEST 1: Batch Read (All Fields at Once)")
    print("-" * 80)
    
    field_ids = list(LOAN_SUMMARY_FIELDS.keys())
    
    # Show API details for debugging
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    print(f"\nAPI Configuration:")
    print(f"  Base URL: {api_base_url}")
    print(f"  Endpoint: POST /encompass/v3/loans/{loan_id}/fieldReader")
    print(f"  Fields to read: {len(field_ids)}")
    print()
    
    try:
        print(f"Attempting to read {len(field_ids)} fields in one call...")
        result = read_fields(loan_id, field_ids)
        
        print("✓ Batch read successful!")
        print(f"\nResults:")
        
        success_count = 0
        empty_count = 0
        
        for field_id, field_name in LOAN_SUMMARY_FIELDS.items():
            value = result.get(field_id)
            
            if value is not None:
                success_count += 1
                value_str = str(value)
                # Truncate long values
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                print(f"  ✓ {field_id:6} ({field_name:40}) = {value_str}")
            else:
                empty_count += 1
                print(f"  ○ {field_id:6} ({field_name:40}) = (empty)")
        
        print(f"\nSummary:")
        print(f"  Fields with values: {success_count}")
        print(f"  Empty fields: {empty_count}")
        print(f"  Total: {len(field_ids)}")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Batch read failed: {error_msg}")
        
        if "401" in error_msg:
            print("\n⚠️ 401 AUTHENTICATION ERROR")
            print("  This means:")
            print("  - Your credentials are invalid or expired")
            print("  - The OAuth2 token generation failed")
            print("  - The client ID/secret/instance ID may be incorrect")
            print("\n  To fix:")
            print("  1. Check your Encompass admin portal")
            print("  2. Verify your credentials in .env file:")
            print("     - ENCOMPASS_CLIENT_ID")
            print("     - ENCOMPASS_CLIENT_SECRET")
            print("     - ENCOMPASS_INSTANCE_ID")
            print("  3. Ensure credentials match your Encompass environment")
        elif "404" in error_msg:
            print("\n⚠️ 404 NOT FOUND ERROR")
            print(f"  Loan ID '{loan_id}' may not exist or is not accessible")
        elif "403" in error_msg:
            print("\n⚠️ 403 FORBIDDEN ERROR")
            print("  Your credentials work but don't have permission to access this loan")
        
        # Test 2: Try reading fields individually
        print("\n" + "-" * 80)
        print("TEST 2: Individual Field Reads (Fallback)")
        print("-" * 80)
        
        print("\nAttempting to read each field individually...\n")
        
        individual_results = {}
        success_count = 0
        fail_count = 0
        
        for field_id, field_name in LOAN_SUMMARY_FIELDS.items():
            try:
                value = read_field(loan_id, field_id)
                
                if value is not None:
                    success_count += 1
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:50] + "..."
                    print(f"  ✓ {field_id:6} ({field_name:40}) = {value_str}")
                    individual_results[field_id] = value
                else:
                    print(f"  ○ {field_id:6} ({field_name:40}) = (empty)")
                    individual_results[field_id] = None
                    
            except Exception as field_error:
                fail_count += 1
                print(f"  ✗ {field_id:6} ({field_name:40}) - Error: {str(field_error)[:50]}")
                individual_results[field_id] = None
        
        print(f"\nIndividual Read Summary:")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {fail_count}")
        print(f"  Empty: {len(field_ids) - success_count - fail_count}")
        
        if success_count == 0:
            print("\n✗ NO FIELDS COULD BE READ")
            print("  The Encompass connection is not working.")
            return None
        else:
            return individual_results
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


def main():
    """Run field tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test all loan summary fields")
    parser.add_argument(
        "--loan-id",
        type=str,
        default="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
        help="Loan ID to test"
    )
    
    args = parser.parse_args()
    
    result = test_all_fields(args.loan_id)
    
    if result:
        print("\n\n📋 FIELD VALUES RETRIEVED")
        print("─" * 40)
        
        # Show key fields
        key_fields = {
            "1172": "Loan Type",
            "19": "Loan Purpose",
            "14": "Property State",
            "1109": "Loan Amount",
            "353": "LTV",
        }
        
        for field_id, name in key_fields.items():
            value = result.get(field_id)
            if value is not None:
                print(f"{name}: {value}")
            else:
                print(f"{name}: (empty)")
    else:
        print("\n\n✗ FAILED TO RETRIEVE FIELD VALUES")
        print("─" * 40)
        print("Please check your Encompass credentials and loan ID")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

