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

import json
import requests
from dotenv import load_dotenv
from packages.shared import read_field, read_fields
from packages.shared.auth import get_access_token

# Load .env from project root
env_path = project_root / ".env"
load_dotenv(env_path)


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

# TRID / Loan Estimate fields for testing
TRID_LE_FIELDS = {
    "LE1.X1": "LE Date Issued",
    "745": "Application Date",
    "DISCLOSURE.X1": "LE Sent Date (alt)",
    "3152": "LE Due Date",
    "762": "Initial Disclosure Sent Date",
    "3168": "Initial Disclosure Received Date",
}

# All fields from test_loan_data_happy_path.json for Disclosure Agent v2
HAPPY_PATH_FIELDS = {
    # MVP Eligibility
    "1172": "Loan Type",
    "14": "Property State",
    "19": "Loan Purpose",
    
    # TRID Compliance
    "745": "Application Date",
    "LE1.X1": "LE Date Issued",
    "3152": "LE Due Date / Disclosure Sent Date",
    "761": "Lock Date",
    "762": "Lock Expiration Date",
    "2400": "Rate Locked Indicator",
    
    # Borrower Info (1003 URLA)
    "4000": "Borrower First Name",
    "4002": "Borrower Last Name",
    "65": "Borrower SSN",
    "1240": "Borrower Email",
    "1402": "Borrower DOB",
    
    # Property Info
    "11": "Property Street Address",
    "12": "Property City",
    "15": "Property Zip",
    "1041": "Property Type",
    "1811": "Occupancy Type",
    
    # Loan Terms
    "1109": "Loan Amount",
    "3": "Interest Rate",
    "4": "Loan Term (months)",
    "353": "LTV",
    "976": "CLTV",
    "356": "Appraised Value",
    "136": "Purchase Price",
    
    # RegZ-LE Fields
    "1176": "Interest Days Per Year",
    "3514": "0% Payment Option",
    "3515": "Use Simple Interest Accrual",
    "3516": "Biweekly/Interim Interest Days",
    "672": "Late Charge Days",
    "673": "Late Charge Percent",
    "3517": "Assumption Text",
    "1751": "Buydown Marked",
    "664": "Prepayment Indicator",
    
    # Cash to Close Fields
    "NEWHUD2.X55": "Use Actual Down Payment",
    "NEWHUD2.X56": "Closing Costs Financed",
    "NEWHUD2.X57": "Include Payoffs in Adjustments",
    "NEWHUD2.X58": "Alternative Form Checkbox (Refi)",
    "LE1.X77": "Displayed CTC (LE Page 2)",
    
    # ATR/QM Fields
    "ATRQM.X1": "ATR/QM Loan Features Flag",
    "ATRQM.X2": "ATR/QM Points and Fees Flag",
    "ATRQM.X3": "ATR/QM Price Limit Flag",
    
    # LO Info
    "317": "LO Name",
    "3238": "LO NMLS ID",
    "3330": "Company NMLS",
    
    # Status Fields
    "2626": "Channel",
    "1393": "Current Status",
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


def get_full_loan_details(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6", save_to_file: bool = True):
    """Get ALL loan details from Encompass.
    
    Uses GET /encompass/v3/loans/{loanId} to retrieve the complete loan object.
    
    Args:
        loan_id: Encompass loan GUID
        save_to_file: If True, saves the full response to a JSON file
        
    Returns:
        dict: Full loan object or None if failed
    """
    print("\n" + "=" * 80)
    print("GETTING FULL LOAN DETAILS")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        print(f"\n✅ Token generated: {token[:15]}...")
    except Exception as e:
        print(f"\n❌ Failed to generate token: {e}")
        return None
    
    # Make the API call
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}"
    
    print(f"\nAPI Call: GET {url}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            loan_data = response.json()
            
            # Show key info
            print("\n" + "-" * 80)
            print("LOAN SUMMARY")
            print("-" * 80)
            
            # Extract key fields from the loan object
            if "applications" in loan_data and loan_data["applications"]:
                app = loan_data["applications"][0]
                app_id = app.get("id", "N/A")
                print(f"  Application ID: {app_id}")
                
                # Borrower info
                if "borrower" in app:
                    borrower = app["borrower"]
                    name = f"{borrower.get('firstName', '')} {borrower.get('lastName', '')}".strip()
                    print(f"  Borrower: {name}")
                    print(f"  Email: {borrower.get('emailAddressText', 'N/A')}")
            
            # Loan info
            print(f"\n  Loan Number: {loan_data.get('loanNumber', 'N/A')}")
            print(f"  Loan Amount: {loan_data.get('borrowerRequestedLoanAmount', 'N/A')}")
            print(f"  Interest Rate: {loan_data.get('currentInterestRate', 'N/A')}")
            
            # Property info
            if "property" in loan_data:
                prop = loan_data["property"]
                addr = f"{prop.get('streetAddress', '')} {prop.get('city', '')}, {prop.get('state', '')} {prop.get('postalCode', '')}"
                print(f"  Property: {addr.strip()}")
            
            # Dates
            print(f"\n  Application Date: {loan_data.get('applicationDate', 'N/A')}")
            print(f"  Expected Close: {loan_data.get('closingDate', 'N/A')}")
            
            # Show top-level keys
            print("\n" + "-" * 80)
            print("TOP-LEVEL KEYS IN LOAN OBJECT")
            print("-" * 80)
            keys = sorted(loan_data.keys())
            for i, key in enumerate(keys):
                val = loan_data[key]
                val_type = type(val).__name__
                if isinstance(val, list):
                    val_preview = f"[{len(val)} items]"
                elif isinstance(val, dict):
                    val_preview = f"{{...}} ({len(val)} keys)"
                elif isinstance(val, str) and len(val) > 40:
                    val_preview = f'"{val[:40]}..."'
                else:
                    val_preview = repr(val)
                print(f"  {key:<40} ({val_type}) = {val_preview}")
            
            print(f"\n  Total top-level keys: {len(keys)}")
            
            # Save to file
            if save_to_file:
                output_file = f"loan_details_{loan_id[:8]}.json"
                with open(output_file, "w") as f:
                    json.dump(loan_data, f, indent=2, default=str)
                print(f"\n📄 Full loan object saved to: {output_file}")
            
            return loan_data
            
        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        return None


def test_trid_fields(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"):
    """Test reading TRID/LE fields specifically.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        dict: Field values or None if failed
    """
    print("\n" + "=" * 80)
    print("TESTING TRID / LOAN ESTIMATE FIELDS")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    print(f"Fields to test: {len(TRID_LE_FIELDS)}")
    
    # Check credentials first
    has_creds = check_credentials()
    
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Generate token if needed
    if not os.getenv("ENCOMPASS_ACCESS_TOKEN"):
        try:
            token = get_access_token()
            print(f"\n✅ OAuth2 token generated: {token[:15]}...")
        except Exception as e:
            print(f"\n❌ Failed to generate token: {e}")
            return None
    
    field_ids = list(TRID_LE_FIELDS.keys())
    
    print(f"\n{'Field ID':<20} {'Description':<35} {'Value'}")
    print("-" * 80)
    
    results = {}
    
    # Test each field individually (some may use different formats)
    for field_id, field_name in TRID_LE_FIELDS.items():
        try:
            value = read_field(loan_id, field_id)
            results[field_id] = value
            
            if value is not None and value != "":
                value_str = str(value)[:30]
                print(f"✓ {field_id:<18} {field_name:<35} {value_str}")
            else:
                print(f"○ {field_id:<18} {field_name:<35} (empty)")
                
        except Exception as e:
            error_str = str(e)[:40]
            print(f"✗ {field_id:<18} {field_name:<35} ERROR: {error_str}")
            results[field_id] = None
    
    print("-" * 80)
    
    # Summary
    found = sum(1 for v in results.values() if v is not None and v != "")
    empty = sum(1 for v in results.values() if v == "" or v is None)
    
    print(f"\nSummary: {found} with values, {empty} empty/not found")
    
    return results


def test_happy_path_fields(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6", save_to_file: bool = True):
    """Test ALL fields from test_loan_data_happy_path.json using field reader API.
    
    This tests if each field ID exists and what value it currently has.
    
    Args:
        loan_id: Encompass loan GUID
        save_to_file: If True, saves results to JSON file
        
    Returns:
        dict: Field verification results with values
    """
    print("\n" + "=" * 80)
    print("TESTING HAPPY PATH FIELDS (Disclosure Agent v2)")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    print(f"Total fields to test: {len(HAPPY_PATH_FIELDS)}")
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        if not token:
            print("✗ Failed to get access token")
            return None
        print(f"✓ Got access token")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    # Test each field
    field_ids = list(HAPPY_PATH_FIELDS.keys())
    
    print(f"\n📡 Reading {len(field_ids)} fields via Field Reader API...")
    print("-" * 80)
    
    results = {
        "loan_id": loan_id,
        "total_fields": len(field_ids),
        "fields_found": 0,
        "fields_empty": 0,
        "fields_error": 0,
        "details": {}
    }
    
    # Group fields by category for cleaner output
    categories = {
        "MVP Eligibility": ["1172", "14", "19"],
        "TRID Compliance": ["745", "LE1.X1", "3152", "761", "762", "2400"],
        "Borrower Info": ["4000", "4002", "65", "1240", "1402"],
        "Property Info": ["11", "12", "15", "1041", "1811"],
        "Loan Terms": ["1109", "3", "4", "353", "976", "356", "136"],
        "RegZ-LE": ["1176", "3514", "3515", "3516", "672", "673", "3517", "1751", "664"],
        "Cash to Close": ["NEWHUD2.X55", "NEWHUD2.X56", "NEWHUD2.X57", "NEWHUD2.X58", "LE1.X77"],
        "ATR/QM": ["ATRQM.X1", "ATRQM.X2", "ATRQM.X3"],
        "LO Info": ["317", "3238", "3330"],
        "Status": ["2626", "1393"],
    }
    
    for category, cat_fields in categories.items():
        print(f"\n📋 {category}")
        print("-" * 60)
        
        for field_id in cat_fields:
            field_name = HAPPY_PATH_FIELDS.get(field_id, "Unknown")
            
            try:
                value = read_field(loan_id, field_id)
                
                if value is not None and value != "" and value != "//":
                    status = "✓"
                    results["fields_found"] += 1
                    display_val = str(value)[:40]
                else:
                    status = "○"  # Empty/blank
                    results["fields_empty"] += 1
                    display_val = "(empty)"
                
                results["details"][field_id] = {
                    "name": field_name,
                    "value": value,
                    "exists": True,
                    "has_value": value is not None and value != "" and value != "//"
                }
                
                print(f"{status} {field_id:<18} {field_name:<30} = {display_val}")
                
            except Exception as e:
                results["fields_error"] += 1
                results["details"][field_id] = {
                    "name": field_name,
                    "value": None,
                    "exists": False,
                    "error": str(e)[:50]
                }
                print(f"✗ {field_id:<18} {field_name:<30} = ERROR: {str(e)[:30]}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Fields with values:  {results['fields_found']}")
    print(f"  Fields empty/blank:  {results['fields_empty']}")
    print(f"  Fields with errors:  {results['fields_error']}")
    print(f"  Total tested:        {results['total_fields']}")
    
    # Highlight critical missing fields
    critical_fields = ["745", "LE1.X1", "1172", "14", "19", "ATRQM.X1", "ATRQM.X2", "ATRQM.X3"]
    missing_critical = []
    for fid in critical_fields:
        detail = results["details"].get(fid, {})
        if not detail.get("has_value", False):
            missing_critical.append(f"{fid} ({HAPPY_PATH_FIELDS.get(fid, 'Unknown')})")
    
    if missing_critical:
        print(f"\n⚠️ CRITICAL FIELDS MISSING/EMPTY:")
        for f in missing_critical:
            print(f"   - {f}")
    
    # Save to file
    if save_to_file:
        filename = f"happy_path_field_test_{loan_id[:8]}.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {filename}")
    
    return results


def verify_field_ids(field_ids: list, save_to_file: bool = True):
    """Verify field IDs exist using Encompass Schema API.
    
    Uses GET /encompass/v3/schemas/loan/standardFields?ids=... to verify fields.
    
    Args:
        field_ids: List of field IDs to verify
        save_to_file: If True, saves results to JSON file
        
    Returns:
        dict: Field verification results
    """
    print("\n" + "=" * 80)
    print("VERIFYING FIELD IDs VIA ENCOMPASS SCHEMA API")
    print("=" * 80)
    print(f"\nFields to verify: {len(field_ids)}")
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        if not token:
            print("✗ Failed to get access token")
            return None
        print(f"✓ Got access token")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    # Get API server (use same env var as rest of codebase)
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    # Prepare field IDs (join with comma)
    ids_param = ",".join(field_ids)
    
    # Call schema API
    url = f"{api_server}/encompass/v3/schemas/loan/standardFields"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"ids": ids_param}
    
    print(f"\n📡 Calling Schema API...")
    print(f"   URL: {url}")
    print(f"   Fields: {len(field_ids)} requested")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse results
            found_fields = {}
            not_found = []
            
            if isinstance(data, list):
                for field_info in data:
                    field_id = field_info.get("id") or field_info.get("fieldId")
                    if field_id:
                        found_fields[field_id] = {
                            "id": field_id,
                            "description": field_info.get("description", ""),
                            "format": field_info.get("format", ""),
                            "type": field_info.get("type", ""),
                            "readOnly": field_info.get("readOnly", False),
                            "options": field_info.get("options", [])
                        }
            elif isinstance(data, dict):
                # Single field or different format
                for field_id, field_info in data.items():
                    found_fields[field_id] = field_info
            
            # Check which fields were not found
            for fid in field_ids:
                if fid not in found_fields:
                    not_found.append(fid)
            
            # Display results
            print(f"\n✓ Found: {len(found_fields)} fields")
            print(f"✗ Not found: {len(not_found)} fields")
            
            print("\n" + "-" * 80)
            print(f"{'Field ID':<20} {'Description':<40} {'Type':<15}")
            print("-" * 80)
            
            for fid in field_ids:
                if fid in found_fields:
                    info = found_fields[fid]
                    desc = info.get("description", "")[:38]
                    ftype = info.get("format") or info.get("type", "")
                    print(f"✓ {fid:<18} {desc:<40} {ftype:<15}")
                else:
                    print(f"✗ {fid:<18} {'NOT FOUND':<40} {'':<15}")
            
            print("-" * 80)
            
            result = {
                "verified": len(found_fields),
                "not_found": len(not_found),
                "fields": found_fields,
                "missing": not_found
            }
            
            # Save to file
            if save_to_file and found_fields:
                filename = "field_schema_verification.json"
                with open(filename, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n📄 Saved to: {filename}")
            
            return result
            
        else:
            print(f"✗ API Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def get_all_standard_fields(limit: int = 1000, save_to_file: bool = True):
    """Get list of all standard fields from Encompass Schema API.
    
    Uses GET /encompass/v3/schemas/loan/standardFields to get all fields.
    
    Args:
        limit: Max number of fields to retrieve
        save_to_file: If True, saves results to JSON file
        
    Returns:
        list: List of field definitions
    """
    print("\n" + "=" * 80)
    print("GETTING ALL STANDARD FIELDS FROM ENCOMPASS")
    print("=" * 80)
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        if not token:
            print("✗ Failed to get access token")
            return None
        print(f"✓ Got access token")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    # Get API server (use same env var as rest of codebase)
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    # Call schema API
    url = f"{api_server}/encompass/v3/schemas/loan/standardFields"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"start": 0, "limit": limit}
    
    print(f"\n📡 Calling Schema API...")
    print(f"   URL: {url}")
    print(f"   Limit: {limit}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✓ Retrieved {len(data)} fields")
            
            # Save to file
            if save_to_file:
                filename = "all_standard_fields.json"
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"\n📄 Saved to: {filename}")
                
                # Also create a simple lookup file
                lookup = {}
                for field in data:
                    fid = field.get("id") or field.get("fieldId")
                    if fid:
                        lookup[fid] = field.get("description", "")
                
                with open("field_id_lookup.json", "w") as f:
                    json.dump(lookup, f, indent=2, sort_keys=True)
                print(f"📄 Saved lookup to: field_id_lookup.json")
            
            return data
            
        else:
            print(f"✗ API Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def get_disclosure_tracking_logs(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6", save_to_file: bool = True):
    """Get disclosure tracking logs for a loan.
    
    Uses GET /encompass/v3/loans/{loanId}/disclosureTracking2015Logs
    
    This tells us:
    - If Initial LE has already been sent (contents contains "LE")
    - If this is a COC/Revised LE scenario
    - eConsent status, Intent to Proceed, etc.
    
    Args:
        loan_id: Loan GUID
        save_to_file: If True, saves results to JSON file
        
    Returns:
        list: List of disclosure tracking log objects
    """
    print("\n" + "=" * 80)
    print("FETCHING DISCLOSURE TRACKING LOGS")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        if not token:
            print("✗ Failed to get access token")
            return None
        print(f"✓ Got access token")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    # Get API server
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    # Build URL
    url = f"{api_server}/encompass/v3/loans/{loan_id}/disclosureTracking2015Logs"
    
    print(f"\nFetching disclosure tracking from:")
    print(f"  GET {url}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            logs = response.json()
            
            print(f"\n✓ Retrieved {len(logs)} disclosure tracking entries")
            
            if len(logs) == 0:
                print("\n📋 No disclosures sent yet - ELIGIBLE for Initial LE")
            else:
                print("\n" + "-" * 80)
                print(f"{'#':<4} {'Type':<10} {'Contents':<25} {'Method':<15} {'Date'}")
                print("-" * 80)
                
                le_sent = False
                cd_sent = False
                
                for i, log in enumerate(logs):
                    contents = log.get("contents", [])
                    contents_str = ", ".join(contents) if contents else "N/A"
                    method = log.get("disclosedMethod", "N/A")
                    disclosed_date = log.get("disclosedDate", "")[:10] if log.get("disclosedDate") else ""
                    
                    # Determine type
                    if "LE" in contents:
                        log_type = "LE"
                        le_sent = True
                    elif "CD" in contents:
                        log_type = "CD"
                        cd_sent = True
                    else:
                        log_type = "Other"
                    
                    print(f"{i+1:<4} {log_type:<10} {contents_str[:25]:<25} {method:<15} {disclosed_date}")
                
                print("-" * 80)
                
                # Summary
                print(f"\n📊 DISCLOSURE STATUS:")
                print(f"   Initial LE Sent: {'✓ Yes' if le_sent else '✗ No'}")
                print(f"   CD Sent: {'✓ Yes' if cd_sent else '✗ No'}")
                
                if le_sent:
                    print(f"\n⚠️  Initial LE already sent - this would be COC/Revised LE (not MVP)")
                else:
                    print(f"\n✓ No LE sent yet - ELIGIBLE for Initial LE")
            
            # Save to file
            if save_to_file:
                filename = f"disclosure_tracking_{loan_id[:8]}.json"
                with open(filename, "w") as f:
                    json.dump(logs, f, indent=2)
                print(f"\n📄 Saved to: {filename}")
            
            return logs
            
        else:
            print(f"✗ API Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_loan_milestones(loan_id: str = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6", save_to_file: bool = True):
    """Get all milestones for a loan.
    
    Uses GET /encompass/v3/loans/{loanId}/milestones to retrieve milestone logs.
    
    Args:
        loan_id: Loan GUID
        save_to_file: If True, saves results to JSON file
        
    Returns:
        list: List of milestone objects
    """
    print("\n" + "=" * 80)
    print("FETCHING LOAN MILESTONES")
    print("=" * 80)
    print(f"\nLoan ID: {loan_id}")
    
    # Check credentials
    has_creds = check_credentials()
    if not has_creds:
        print("\n⚠️ Cannot proceed without Encompass credentials")
        return None
    
    # Get token
    try:
        token = get_access_token()
        if not token:
            print("✗ Failed to get access token")
            return None
        print(f"✓ Got access token")
    except Exception as e:
        print(f"✗ Auth error: {e}")
        return None
    
    # Get API server
    api_server = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    # Build URL
    url = f"{api_server}/encompass/v3/loans/{loan_id}/milestones"
    
    print(f"\nFetching milestones from:")
    print(f"  GET {url}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            milestones = response.json()
            
            print(f"\n✓ Retrieved {len(milestones)} milestones")
            print("\n" + "-" * 80)
            print(f"{'#':<4} {'Milestone Name':<35} {'Done?':<8} {'Date':<12} {'ID'}")
            print("-" * 80)
            
            for i, ms in enumerate(milestones):
                name = ms.get("name", "Unknown")[:35]  # Fixed: "name" not "milestoneName"
                done = "✓ Yes" if ms.get("doneIndicator") else "No"  # Fixed: "doneIndicator" not "done"
                done_date = ms.get("doneDate", "")[:10] if ms.get("doneDate") else ""
                ms_id = ms.get("id", "")[:20]
                
                print(f"{i+1:<4} {name:<35} {done:<8} {done_date:<12} {ms_id}")
            
            print("-" * 80)
            
            # Show current milestone (last completed one)
            completed = [m for m in milestones if m.get("doneIndicator")]
            if completed:
                current = completed[-1]
                print(f"\n📍 Current Stage: {current.get('name', 'Unknown')}")
                print(f"   Completed: {current.get('doneDate', 'N/A')}")
            
            # Show next milestone (first incomplete one)
            incomplete = [m for m in milestones if not m.get("doneIndicator")]
            if incomplete:
                next_ms = incomplete[0]
                print(f"\n⏭️  Next Milestone: {next_ms.get('name', 'Unknown')}")
                expected = next_ms.get("expectedDate")
                if expected:
                    print(f"   Expected: {expected[:10]}")
            
            # Save to file
            if save_to_file:
                filename = f"milestones_{loan_id[:8]}.json"
                with open(filename, "w") as f:
                    json.dump(milestones, f, indent=2)
                print(f"\n📄 Saved to: {filename}")
            
            return milestones
            
        else:
            print(f"✗ API Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


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
    parser.add_argument(
        "--trid",
        action="store_true",
        help="Test TRID/LE fields instead of loan summary fields"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Get full loan details (saves to JSON file)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify field IDs exist using Schema API"
    )
    parser.add_argument(
        "--all-fields",
        action="store_true",
        help="Get all standard fields from Schema API"
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="Comma-separated field IDs to verify (use with --verify)"
    )
    parser.add_argument(
        "--happy-path",
        action="store_true",
        help="Test all fields from test_loan_data_happy_path.json"
    )
    parser.add_argument(
        "--milestones",
        action="store_true",
        help="Get all milestones for the loan"
    )
    parser.add_argument(
        "--disclosure-tracking",
        action="store_true",
        help="Get disclosure tracking logs (check if LE/CD already sent)"
    )
    parser.add_argument(
        "--pre-check",
        action="store_true",
        help="Run full pre-check: milestones + disclosure tracking + TRID dates"
    )
    
    args = parser.parse_args()
    
    # Handle pre-check (comprehensive eligibility check)
    if args.pre_check:
        print("\n" + "=" * 80)
        print("DISCLOSURE ELIGIBILITY PRE-CHECK")
        print("=" * 80)
        
        loan_id = args.loan_id
        eligible = True
        issues = []
        
        # 1. Check milestones
        print("\n[1/3] Checking milestones...")
        milestones = get_loan_milestones(loan_id, save_to_file=False)
        if milestones:
            completed = [m.get("name", "Unknown") for m in milestones if m.get("doneIndicator")]
            incomplete = [m.get("name", "Unknown") for m in milestones if not m.get("doneIndicator")]
            
            print(f"   Completed milestones: {completed if completed else 'None'}")
            print(f"   Pending milestones: {len(incomplete)}")
            
            # Check if loan is too far along (Funding/Completion)
            blocking_done = ["Funding", "Post Closing", "Shipping", "Completion"]
            for ms in completed:
                if ms in blocking_done:
                    eligible = False
                    issues.append(f"Milestone '{ms}' already completed - loan may be funded")
            
            # Check if at least Started (or Qualification)
            if "Started" not in completed and "Qualification" not in completed:
                # Log but don't block - some workflows skip "Started"
                print(f"   ⚠️ Note: Neither 'Started' nor 'Qualification' milestone completed")
        else:
            issues.append("Could not fetch milestones")
        
        # 2. Check disclosure tracking
        print("\n[2/3] Checking disclosure tracking...")
        dt_logs = get_disclosure_tracking_logs(loan_id, save_to_file=False)
        if dt_logs is not None:
            le_sent = any("LE" in log.get("contents", []) for log in dt_logs)
            if le_sent:
                eligible = False
                issues.append("Initial LE already sent - would need COC/Revised LE (not MVP)")
        else:
            issues.append("Could not fetch disclosure tracking")
        
        # 3. Check TRID fields
        print("\n[3/3] Checking TRID compliance fields...")
        trid_fields = read_fields(loan_id, ["745", "3152", "LE1.X1", "762"])
        app_date = trid_fields.get("745")
        le_due = trid_fields.get("3152")
        le_issued = trid_fields.get("LE1.X1")
        
        if not app_date or app_date in ["//", ""]:
            eligible = False
            issues.append("Application Date (745) not set")
        else:
            print(f"   Application Date: {app_date}")
            
            # Check if LE due date passed (simple check - would need proper date parsing)
            if le_due:
                print(f"   LE Due Date: {le_due}")
        
        if le_issued:
            print(f"   LE Date Issued: {le_issued}")
        
        # Summary
        print("\n" + "=" * 80)
        print("PRE-CHECK SUMMARY")
        print("=" * 80)
        
        if eligible and not issues:
            print("\n✅ ELIGIBLE for Initial LE Disclosure")
            print("   - Milestones: OK")
            print("   - No LE sent yet: OK")
            print("   - TRID dates: OK")
        else:
            print("\n❌ NOT ELIGIBLE for Initial LE Disclosure")
            print("\nIssues found:")
            for issue in issues:
                print(f"   ⚠️ {issue}")
        
        return 0 if eligible else 1
    
    # Handle milestones request
    if args.milestones:
        result = get_loan_milestones(args.loan_id)
        return 0 if result else 1
    
    # Handle disclosure tracking request
    if args.disclosure_tracking:
        result = get_disclosure_tracking_logs(args.loan_id)
        return 0 if result else 1
    
    # Handle schema API operations
    if args.all_fields:
        result = get_all_standard_fields()
        if result:
            print(f"\n\n✓ Retrieved {len(result)} standard fields")
        return 0 if result else 1
    
    # Test happy path fields
    if args.happy_path:
        result = test_happy_path_fields(args.loan_id)
        if result:
            print(f"\n\n✓ Tested {result['total_fields']} fields: {result['fields_found']} with values, {result['fields_empty']} empty, {result['fields_error']} errors")
        return 0 if result else 1
    
    if args.verify:
        # Get field IDs to verify
        if args.fields:
            field_ids = [f.strip() for f in args.fields.split(",")]
        else:
            # Default: verify all disclosure-related fields
            field_ids = list(LOAN_SUMMARY_FIELDS.keys()) + list(TRID_LE_FIELDS.keys())
        
        result = verify_field_ids(field_ids)
        if result:
            print(f"\n\n✓ Verified {result['verified']} fields, {result['not_found']} not found")
        return 0 if result else 1
    
    # Handle loan data operations
    if args.full:
        result = get_full_loan_details(args.loan_id)
    elif args.trid:
        result = test_trid_fields(args.loan_id)
    else:
        result = test_all_fields(args.loan_id)
    
    if result:
        print("\n\n📋 FIELD VALUES RETRIEVED")
        print("─" * 40)
        
        if args.full:
            # For full loan details, just show application ID (key for eDisclosures)
            if "applications" in result and result["applications"]:
                print(f"Application ID: {result['applications'][0].get('id', 'N/A')}")
            print("(See JSON file for complete loan data)")
        elif args.trid:
            # Show TRID/LE fields
            key_fields = {
                "LE1.X1": "LE Date Issued",
                "745": "Application Date",
                "3152": "LE Due Date",
            }
            for field_id, name in key_fields.items():
                value = result.get(field_id)
                if value is not None:
                    print(f"{name}: {value}")
                else:
                    print(f"{name}: (empty)")
        else:
            # Show key loan summary fields
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

