#!/usr/bin/env python3
"""
Fetch loan information from Encompass.

Pulls loan context, key fields, and available documents for a given loan ID.
Uses shared Encompass helpers for authentication consistency across the project.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path for shared imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import shared Encompass utilities for consistent auth across project
from packages.shared import get_access_token

# =============================================================================
# LOAN ID TO FETCH
# =============================================================================
LOAN_ID = "59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc"


def get_http_client():
    """Get HTTP client for Encompass API requests using shared auth."""
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    print(f"[AUTH] API Base URL: {api_base_url}")
    print(f"[AUTH] Using shared get_access_token() for authentication...")
    
    # Use shared auth module for consistency with rest of project
    access_token = get_access_token()
    
    if not access_token:
        raise RuntimeError("Failed to get access token from shared auth module")
    
    print(f"[AUTH] ✓ Got access token: {access_token[:20]}...")
    
    return api_base_url, access_token


def fetch_loan_fields(api_base_url: str, token: str, loan_id: str) -> dict:
    """Fetch key loan fields using Field Reader API."""
    import requests
    
    # COMPREHENSIVE field list - Encompass has thousands of fields
    # This is a much broader query to discover what's populated
    # Use list(dict.fromkeys(...)) to preserve order while deduplicating
    field_ids_raw = [
        # =====================================================================
        # LOAN IDENTIFICATION & PROGRAM
        # =====================================================================
        "364",    # Loan Number
        "1172",   # Loan Type
        "1401",   # Loan Program
        "19",     # Loan Purpose
        "420",    # Mortgage Type
        "1393",   # Loan Program Name
        "1544",   # Product Code
        "608",    # Amortization Type
        "1659",   # Loan Channel
        "2626",   # ARM Description
        
        # =====================================================================
        # BORROWER INFORMATION
        # =====================================================================
        "4000",   # Borrower First Name
        "4001",   # Borrower Middle Name
        "4002",   # Borrower Last Name
        "4003",   # Borrower Suffix
        "36",     # Borrower Full Name
        "65",     # Borrower SSN
        "1268",   # Borrower Email
        "66",     # Borrower Home Phone
        "1490",   # Borrower Cell Phone
        "84",     # Borrower Work Phone
        "52",     # Borrower DOB
        "1240",   # Borrower Age
        "471",    # Borrower Marital Status
        "1523",   # Borrower Citizenship
        "1066",   # Borrower Years in School
        "1199",   # Borrower Dependents Number
        
        # Borrower Current Address
        "FR0104", # Borrower Current Street
        "FR0106", # Borrower Current City
        "FR0107", # Borrower Current State
        "FR0108", # Borrower Current Zip
        "1402",   # Borrower Years at Current Address
        
        # Borrower Mailing Address
        "URLA.X73",  # Borrower Mailing Street
        "URLA.X75",  # Borrower Mailing City
        "URLA.X76",  # Borrower Mailing State
        "URLA.X77",  # Borrower Mailing Zip
        
        # Borrower Employment
        "BE0015",   # Borrower Employer Name
        "BE0003",   # Borrower Job Title
        "BE0016",   # Borrower Employer Street
        "BE0018",   # Borrower Employer City
        "BE0019",   # Borrower Employer State
        "BE0020",   # Borrower Employer Zip
        "BE0012",   # Borrower Employer Phone
        "BE0002",   # Borrower Self Employed
        "BE0005",   # Borrower Years on Job
        "BE0006",   # Borrower Months on Job
        "1756",     # Borrower Years in Profession
        
        # Borrower Income
        "1",        # Borrower Base Income
        "1048",     # Borrower Overtime
        "1049",     # Borrower Bonus
        "1050",     # Borrower Commissions
        "1051",     # Borrower Dividends/Interest
        "1052",     # Borrower Net Rental Income
        "1053",     # Borrower Other Income
        "1759",     # Borrower Total Monthly Income
        
        # =====================================================================
        # CO-BORROWER INFORMATION
        # =====================================================================
        "4004",   # Co-Borrower First Name
        "4005",   # Co-Borrower Middle Name
        "4006",   # Co-Borrower Last Name
        "4007",   # Co-Borrower Suffix
        "68",     # Co-Borrower SSN
        "1519",   # Co-Borrower Email
        "97",     # Co-Borrower Home Phone
        "1520",   # Co-Borrower Cell Phone
        "98",     # Co-Borrower Work Phone
        "1496",   # Co-Borrower DOB
        
        # Co-Borrower Employment
        "CE0015",   # Co-Borrower Employer Name
        "CE0003",   # Co-Borrower Job Title
        
        # =====================================================================
        # PROPERTY INFORMATION
        # =====================================================================
        "11",     # Subject Property Address
        "12",     # Subject Property City
        "14",     # Subject Property State
        "15",     # Subject Property Zip
        "13",     # Subject Property County
        "1041",   # Property Type
        "16",     # Number of Units
        "1811",   # Occupancy Type
        "18",     # Year Built
        "1396",   # Legal Description
        "17",     # Property Rights
        "1981",   # Manufactured Home
        "1026",   # Condo Project Type
        "696",    # HOA
        "232",    # Monthly HOA Dues
        "1397",   # APN (Assessor Parcel Number)
        
        # =====================================================================
        # LOAN AMOUNTS & TERMS
        # =====================================================================
        "1109",   # Loan Amount
        "136",    # Purchase Price
        "356",    # Appraised Value
        "353",    # LTV
        "976",    # CLTV
        "742",    # HCLTV
        "3",      # Interest Rate
        "4",      # Loan Term (months)
        "2",      # Note Rate
        "5",      # P&I Payment
        "912",    # Total Payment
        "1540",   # Total Monthly Payment
        "337",    # Cash to Close
        "1335",   # Down Payment
        "1771",   # Down Payment %
        "6",      # APR
        "1",      # Borrower Base Income
        "1389",   # Total Income
        "736",    # Total Monthly Debt
        "740",    # Front Ratio (DTI)
        "742",    # Back Ratio (DTI)
        "799",    # Total Housing Payment
        
        # =====================================================================
        # FHA/VA/USDA SPECIFIC FIELDS
        # =====================================================================
        "1040",   # FHA Case Number
        "1729",   # FHA MIP Factor
        "337",    # FHA UFMIP
        "1724",   # FHA Monthly MIP
        "232",    # FHA Base Loan Amount
        "2846",   # FHA Total Loan Amount
        "1045",   # VA Case Number
        "1046",   # VA Funding Fee
        "VASUMM.X5",  # VA Entitlement
        "USDA.X1",    # USDA Case Number
        
        # =====================================================================
        # DATES
        # =====================================================================
        "745",    # Application Date
        "748",    # Closing Date
        "682",    # Estimated Closing Date
        "762",    # Lock Date
        "763",    # Lock Expiration Date
        "761",    # Lock Days
        "3152",   # LE Due Date (TRID)
        "CD1.X31", # CD Issue Date
        "LE1.X1",  # LE Issue Date
        "LE1.X4",  # LE Received Date
        "LOG.MS.Date.Started",  # Started Date
        "LOG.MS.Date.Application",  # Application Milestone Date
        "LOG.MS.Date.Processing",   # Processing Date
        "LOG.MS.Date.Approval",     # Approval Date
        "LOG.MS.Date.Clear to Close", # CTC Date
        "LOG.MS.Date.Docs Ordered", # Docs Ordered Date
        "LOG.MS.Date.Funded",       # Funded Date
        
        # =====================================================================
        # LOAN OFFICER & TEAM
        # =====================================================================
        "317",    # LO Name
        "362",    # LO NMLS
        "88",     # LO Email
        "87",     # LO Phone
        "3238",   # LO Company Name
        "3239",   # LO Company NMLS
        "317",    # LO User ID
        "318",    # Processor Name
        "321",    # Processor Email
        "1825",   # Underwriter Name
        "320",    # Closer Name
        "3533",   # Funder Name
        
        # =====================================================================
        # TITLE & ESCROW
        # =====================================================================
        "610",    # Escrow/Title Company Name
        "611",    # Escrow Officer Name
        "613",    # Escrow Company Phone
        "616",    # Escrow Company Email
        "614",    # Escrow Company Address
        "615",    # Escrow Company City
        "VEND.X263", # Title Company State
        
        # =====================================================================
        # CREDIT & UNDERWRITING
        # =====================================================================
        "1055",   # FICO Score (Borrower)
        "4095",   # Equifax Score (Borrower)
        "4096",   # Experian Score (Borrower)
        "4097",   # TransUnion Score (Borrower)
        "1056",   # Credit Score (Used)
        "1057",   # Credit Score Date
        "300",    # AUS Recommendation
        "1543",   # AUS Type
        "3170",   # DU Case ID
        "3171",   # LP Case ID
        "1544",   # AUS Finding
        
        # =====================================================================
        # INSURANCE
        # =====================================================================
        "232",    # Hazard Insurance
        "1660",   # Insurance Company Name
        "334",    # Annual Premium
        "891",    # Monthly Premium
        "338",    # MI Company
        "339",    # MI Monthly Premium
        "340",    # MI Annual Premium
        "353",    # MI Coverage %
        "315",    # Flood Insurance
        "316",    # Flood Zone
        
        # =====================================================================
        # CLOSING COSTS & FEES
        # =====================================================================
        "640",    # Origination Fee
        "641",    # Discount Points
        "1250",   # Total Origination Charges
        "1251",   # Total Services Borrower Can Shop
        "1252",   # Total Services Borrower Cannot Shop
        "1253",   # Total Other Costs
        "1254",   # Total Closing Costs
        "1255",   # Total Prepaid
        "137",    # Earnest Money
        "643",    # Appraisal Fee
        "644",    # Credit Report Fee
        "645",    # Flood Certification Fee
        "647",    # Tax Service Fee
        "648",    # Title Insurance
        "649",    # Lender's Title Insurance
        "650",    # Owner's Title Insurance
        "651",    # Recording Fees
        "652",    # Transfer Taxes
        "974",    # Seller Credits
        "1852",   # Lender Credits
        
        # =====================================================================
        # STATUS & WORKFLOW
        # =====================================================================
        "1393",   # Current Milestone
        "742",    # Loan Status
        "1888",   # Sub-Status
        "CX.LOCKSTATUS",  # Lock Status
        "2301",   # Mavent Status
        "CX.DOCSORDEREDDATE",  # Docs Ordered Date
    ]
    
    # Deduplicate while preserving order
    field_ids = list(dict.fromkeys(field_ids_raw))
    
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/fieldReader"
    
    print(f"\n[FIELDS] Fetching {len(field_ids)} fields from loan {loan_id[:8]}...")
    
    resp = requests.post(
        url,
        json=field_ids,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        params={"invalidFieldBehavior": "Exclude"},
        timeout=60
    )
    
    if resp.status_code != 200:
        print(f"[FIELDS] Request failed: {resp.status_code}")
        print(f"[FIELDS] Response: {resp.text}")
        return {"error": resp.text}
    
    fields = resp.json()
    print(f"[FIELDS] ✓ Retrieved {len(fields)} fields with values")
    
    return fields


def fetch_loan_documents(api_base_url: str, token: str, loan_id: str) -> list:
    """Fetch list of documents in the loan's eFolder."""
    import requests
    
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/attachments"
    
    print(f"\n[DOCUMENTS] Fetching document list from loan {loan_id[:8]}...")
    
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60
    )
    
    if resp.status_code != 200:
        print(f"[DOCUMENTS] Request failed: {resp.status_code}")
        print(f"[DOCUMENTS] Response: {resp.text}")
        return []
    
    documents = resp.json()
    print(f"[DOCUMENTS] ✓ Found {len(documents)} documents/attachments")
    
    return documents


def fetch_milestones(api_base_url: str, token: str, loan_id: str) -> list:
    """Fetch loan milestones using v3 API."""
    import requests
    
    # Use v3 API for consistency with rest of project
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/milestones"
    
    print(f"\n[MILESTONES] Fetching milestones from loan {loan_id[:8]}...")
    
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60
    )
    
    if resp.status_code != 200:
        print(f"[MILESTONES] Request failed: {resp.status_code}")
        return []
    
    milestones = resp.json()
    print(f"[MILESTONES] ✓ Found {len(milestones)} milestones")
    
    return milestones


def main():
    """Main function to fetch and display loan information."""
    print("=" * 80)
    print(f"FETCHING LOAN INFORMATION")
    print(f"Loan ID: {LOAN_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    try:
        # Get authenticated client
        api_base_url, token = get_http_client()
        
        # Fetch loan fields
        fields = fetch_loan_fields(api_base_url, token, LOAN_ID)
        
        # Fetch documents
        documents = fetch_loan_documents(api_base_url, token, LOAN_ID)
        
        # Fetch milestones
        milestones = fetch_milestones(api_base_url, token, LOAN_ID)
        
        # Build result
        result = {
            "loan_id": LOAN_ID,
            "fetch_timestamp": datetime.now().isoformat(),
            "fields": fields,
            "documents": documents,
            "milestones": milestones,
            "summary": {
                "total_fields_with_values": len([v for v in fields.values() if v]),
                "total_documents": len(documents),
                "total_milestones": len(milestones),
            }
        }
        
        # Save to file
        output_file = Path(__file__).parent / f"loan_info_{LOAN_ID[:8]}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n[SAVE] Results saved to: {output_file}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("LOAN SUMMARY")
        print("=" * 80)
        
        # Key loan info
        print("\n📋 LOAN IDENTIFICATION:")
        print(f"   Loan Number:    {fields.get('364', 'N/A')}")
        print(f"   Loan Type:      {fields.get('1172', 'N/A')}")
        print(f"   Loan Program:   {fields.get('1401', 'N/A')}")
        print(f"   Loan Purpose:   {fields.get('384') or fields.get('19', 'N/A')}")
        
        # Borrower info
        print("\n👤 BORROWER:")
        borrower_name = f"{fields.get('4000', '')} {fields.get('4002', '')}".strip()
        print(f"   Name:           {borrower_name or 'N/A'}")
        print(f"   Email:          {fields.get('1268', 'N/A')}")
        print(f"   Phone:          {fields.get('66') or fields.get('1490', 'N/A')}")
        
        # Co-Borrower info
        coborrower_name = f"{fields.get('4004', '')} {fields.get('4006', '')}".strip()
        if coborrower_name:
            print(f"\n👤 CO-BORROWER:")
            print(f"   Name:           {coborrower_name}")
        
        # Property info
        print("\n🏠 PROPERTY:")
        address_parts = [
            fields.get('11', ''),
            fields.get('12', ''),
            fields.get('14', ''),
            fields.get('15', '')
        ]
        address = ', '.join([p for p in address_parts if p])
        print(f"   Address:        {address or 'N/A'}")
        print(f"   Property Type:  {fields.get('1041', 'N/A')}")
        print(f"   Occupancy:      {fields.get('1811') or fields.get('3335', 'N/A')}")
        
        # Loan amounts
        print("\n💰 LOAN AMOUNTS:")
        print(f"   Loan Amount:    ${fields.get('1109', 'N/A')}")
        print(f"   Purchase Price: ${fields.get('136', 'N/A')}")
        print(f"   Appraised Value:${fields.get('356', 'N/A')}")
        print(f"   LTV:            {fields.get('353', 'N/A')}%")
        print(f"   Interest Rate:  {fields.get('3', 'N/A')}%")
        print(f"   Term:           {fields.get('4', 'N/A')} months")
        
        # Dates
        print("\n📅 KEY DATES:")
        print(f"   Application:    {fields.get('745', 'N/A')}")
        print(f"   Closing:        {fields.get('748', 'N/A')}")
        print(f"   Lock Date:      {fields.get('762', 'N/A')}")
        print(f"   Lock Expires:   {fields.get('763', 'N/A')}")
        print(f"   LE Due Date:    {fields.get('3152', 'N/A')}")
        
        # Loan Officer
        print("\n👔 LOAN OFFICER:")
        print(f"   Name:           {fields.get('317', 'N/A')}")
        print(f"   NMLS:           {fields.get('362', 'N/A')}")
        print(f"   Email:          {fields.get('88', 'N/A')}")
        
        # Documents summary
        print("\n📁 DOCUMENTS IN eFOLDER:")
        print(f"   Total:          {len(documents)}")
        
        if documents:
            # Group by title and count
            doc_titles = {}
            for doc in documents:
                title = doc.get('title', 'Unknown')
                doc_titles[title] = doc_titles.get(title, 0) + 1
            
            # Show first 20 unique titles
            sorted_titles = sorted(doc_titles.items(), key=lambda x: x[0])
            print(f"\n   Document Types (showing first 20 of {len(doc_titles)} unique):")
            for title, count in sorted_titles[:20]:
                suffix = f" ({count})" if count > 1 else ""
                print(f"   - {title}{suffix}")
            
            if len(doc_titles) > 20:
                print(f"   ... and {len(doc_titles) - 20} more document types")
        
        # Milestones summary
        print("\n📊 MILESTONES:")
        if milestones:
            for ms in milestones[:10]:
                # v3 API uses "name", v1 used "milestoneName" - support both for compatibility
                name = ms.get('name') or ms.get('milestoneName', 'Unknown')
                done = ms.get('doneIndicator', False)
                status = "Completed" if done else "Pending"
                status_date = ms.get('startDate', '')
                print(f"   - {name}: {status}" + (f" ({status_date[:10]})" if status_date else ""))
        else:
            print("   No milestones found")
        
        print("\n" + "=" * 80)
        print(f"Full details saved to: {output_file}")
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

