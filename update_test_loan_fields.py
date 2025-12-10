"""Update test loan 4b47fb8f to match happy path data with current dates.

This script updates the Encompass loan to have clean test data that aligns
with the happy path test expectations, with dates adjusted for December 9, 2025.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from packages.shared import get_access_token, write_fields

# Test loan ID
LOAN_ID = "4b47fb8f-d597-4ede-84f9-d4e2357ce48e"

# Date calculations (today = December 9, 2025)
TODAY = datetime(2025, 12, 9)
APP_DATE = datetime(2025, 12, 5)  # Friday, Dec 5
LE_DUE_DATE = datetime(2025, 12, 10)  # 3 business days: Mon Dec 8, Tue Dec 9, Wed Dec 10
LOCK_DATE = datetime(2025, 12, 5)  # Same as app date
LOCK_EXPIRATION = datetime(2025, 12, 31)  # End of month
CLOSING_DATE = datetime(2025, 12, 26)  # 15 business days from app date (Dec 5 + ~15 biz days)

print("=" * 80)
print("UPDATE TEST LOAN TO HAPPY PATH DATA")
print("=" * 80)
print(f"Loan ID: {LOAN_ID}")
print(f"Today: {TODAY.strftime('%Y-%m-%d')}")
print()
print("Date Strategy:")
print(f"  Application Date: {APP_DATE.strftime('%Y-%m-%d')} (Friday, 4 days ago)")
print(f"  LE Due Date: {LE_DUE_DATE.strftime('%Y-%m-%d')} (Wed, 3 business days)")
print(f"  Lock Date: {LOCK_DATE.strftime('%Y-%m-%d')} (Same as app date)")
print(f"  Lock Expiration: {LOCK_EXPIRATION.strftime('%Y-%m-%d')} (End of month)")
print(f"  Closing Date: {CLOSING_DATE.strftime('%Y-%m-%d')} (15+ business days)")
print()

# Field updates organized by category
FIELD_UPDATES = {
    # === MVP ELIGIBILITY ===
    "1172": "Conventional",  # Loan Type
    "14": "CA",  # Subject Property State (CA for MVP)
    "19": "Purchase",  # Loan Purpose
    
    # === TRID DATES ===
    "745": APP_DATE.strftime("%Y-%m-%d"),  # Application Date
    "3152": LE_DUE_DATE.strftime("%Y-%m-%d"),  # LE Due Date
    "761": LOCK_DATE.strftime("%Y-%m-%d"),  # Lock Date
    "762": LOCK_EXPIRATION.strftime("%Y-%m-%d"),  # Lock Expiration
    "2400": "Y",  # Rate Locked Indicator
    "748": CLOSING_DATE.strftime("%Y-%m-%d"),  # Closing Date
    
    # === BORROWER INFO ===
    "4000": "ATHENA",  # Borrower First Name
    "4002": "WHITE",  # Borrower Last Name
    "65": "900887799",  # Borrower SSN (no dashes for Encompass)
    "1240": "toktok8calabarzon@gmail.com",  # Borrower Email (HARD STOP)
    "66": "714-488-2888",  # Borrower Home Phone (HARD STOP - using field 66 instead of FE0117)
    "1402": "1978-08-08",  # Borrower DOB
    
    # === PROPERTY INFO ===
    "11": "8080 BALLER ST",  # Subject Property Address
    "12": "Garden Grove",  # Subject Property City
    # "14": "CA",  # Already set above
    "15": "92840",  # Subject Property Zip
    "1041": "Detached",  # Subject Property Type
    "1811": "PrimaryResidence",  # Occupancy Type
    
    # === LOAN FIELDS ===
    "1109": "968877.00",  # Loan Amount
    "3": "6.0",  # Note Rate
    "4": "360",  # Loan Term (months)
    "353": "98.865",  # LTV (> 80%, so MI required)
    "976": "98.865",  # Combined LTV
    "356": "980000",  # Appraised Value
    "136": "980000.00",  # Purchase Price
    
    # === REGZ-LE FIELDS ===
    "1176": "360/360",  # Interest Days Per Year
    "672": "15",  # Late Charge Days
    "674": "5.0",  # Late Charge Percent (Conventional)
    "677": "may not",  # Assumption Text (Conventional)
    "425": "false",  # Buydown Marked (no buydown)
    "2216": "Will not",  # Prepayment Indicator
    
    # === CTC FIELDS (Purchase) ===
    "NEWHUD2.X55": "true",  # Use Actual Down Payment
    "NEWHUD2.X56": "true",  # Closing Costs Financed
    "NEWHUD2.X57": "true",  # Include Payoffs in Adjustments
    "NEWHUD2.X58": "false",  # Alternative Form (only for Refi)
    
    # === STATUS FIELDS ===
    "2626": "Retail",  # Loan Info Channel
    "1393": "Active",  # Loan Status
}

print("Fields to update:")
print("-" * 80)
for field_id, value in sorted(FIELD_UPDATES.items()):
    print(f"  {field_id}: {value}")
print()

# Confirm before proceeding
response = input("Proceed with update? (yes/no): ")
if response.lower() not in ["yes", "y"]:
    print("❌ Update cancelled")
    sys.exit(0)

print()
print("Updating loan fields...")
print("-" * 80)

try:
    # Get access token
    print("🔐 Getting access token...")
    token = get_access_token()
    print("✅ Token obtained")
    
    # Write fields
    print(f"📝 Writing {len(FIELD_UPDATES)} fields to loan {LOAN_ID[:8]}...")
    result = write_fields(LOAN_ID, FIELD_UPDATES)
    
    print()
    print("=" * 80)
    print("✅ UPDATE COMPLETE")
    print("=" * 80)
    print(f"Updated {len(FIELD_UPDATES)} fields successfully!")
    print()
    print("Next steps:")
    print("  1. Verify fields in Encompass")
    print("  2. Run test: cd agents/disclosure && python test_orchestrator.py")
    print()
    
except Exception as e:
    print()
    print("=" * 80)
    print("❌ UPDATE FAILED")
    print("=" * 80)
    print(f"Error: {e}")
    print()
    sys.exit(1)

