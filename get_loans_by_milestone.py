"""
Get all loans in a specific pipeline step/milestone using the Loan Pipeline API.

Example: Get all loans in "DD Requested" milestone.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from packages.shared.auth import get_access_token

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def get_pipeline_field_definitions():
    """Get all available canonical names for pipeline filtering.
    
    This returns all fields that can be used to filter the loan pipeline.
    Look for milestone-related fields like:
    - Loan.MS.CurrentMilestone
    - Fields.1987 (Current Milestone field ID)
    - Loan.MilestoneName
    """
    token = get_access_token()
    api_base = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    url = f"{api_base}/encompass/v1/loanPipeline/fieldDefinitions"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers, timeout=60)
    
    if response.status_code == 200:
        definitions = response.json()
        
        # Filter for milestone-related fields
        print("=" * 80)
        print("MILESTONE-RELATED FIELDS:")
        print("=" * 80)
        
        milestone_fields = [
            field for field in definitions 
            if 'milestone' in field.get('criterionFieldName', '').lower() or
               'milestone' in field.get('description', '').lower()
        ]
        
        for field in milestone_fields:
            print(f"\nCanonical Name: {field.get('criterionFieldName')}")
            print(f"Description: {field.get('description')}")
            print(f"Data Type: {field.get('format')}")
        
        # Also save all definitions for reference
        print("\n" + "=" * 80)
        print(f"Total pipeline fields available: {len(definitions)}")
        print("Saving all definitions to 'pipeline_field_definitions.json'")
        
        import json
        with open('pipeline_field_definitions.json', 'w') as f:
            json.dump(definitions, f, indent=2)
        
        return definitions
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_loans_by_milestone(milestone_name: str, limit: int = 100):
    """Get all loans in a specific milestone/pipeline step.
    
    Args:
        milestone_name: Name of the milestone (e.g., "DD Requested", "Processing", "Doc Preparation")
        limit: Maximum number of loans to return (default 100, max 25000)
    
    Returns:
        List of loan dictionaries with GUIDs and field data
    """
    token = get_access_token()
    api_base = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    url = f"{api_base}/encompass/v1/loanPipeline?limit={limit}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Try different possible canonical names for milestone
    # You'll need to use the correct one from get_pipeline_field_definitions()
    
    # Option 1: Using field ID (1987 = Current Milestone)
    payload_option1 = {
        "filter": [
            {
                "canonicalName": "Fields.1987",  # Current Milestone field
                "value": milestone_name,
                "matchType": "exact"
            }
        ],
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",  # Borrower name
            "Fields.1393",  # Loan status
            "Fields.1987",  # Current milestone
            "Loan.LastModified"
        ]
    }
    
    # Option 2: Using Loan.MS prefix (if available)
    payload_option2 = {
        "filter": [
            {
                "canonicalName": "Loan.MS.CurrentMilestone",
                "value": milestone_name,
                "matchType": "exact"
            }
        ],
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",
            "Fields.1393",
            "Fields.1987",
            "Loan.LastModified"
        ]
    }
    
    # Try option 1 first
    print(f"\n{'='*80}")
    print(f"SEARCHING FOR LOANS IN MILESTONE: {milestone_name}")
    print(f"{'='*80}\n")
    
    print("Trying filter with Fields.1987 (Current Milestone field ID)...")
    response = requests.post(url, json=payload_option1, headers=headers, timeout=60)
    
    if response.status_code == 200:
        loans = response.json()
        print(f"\n✓ Found {len(loans)} loans in milestone '{milestone_name}'")
        
        # Display results
        for idx, loan in enumerate(loans, 1):
            loan_guid = loan.get('loanGuid')
            fields = loan.get('fields', {})
            print(f"\n{idx}. Loan {loan_guid[:8]}...")
            print(f"   Loan Number: {fields.get('Loan.LoanNumber', 'N/A')}")
            print(f"   Borrower: {fields.get('Fields.4', 'N/A')}")
            print(f"   Status: {fields.get('Fields.1393', 'N/A')}")
            print(f"   Milestone: {fields.get('Fields.1987', 'N/A')}")
            print(f"   Last Modified: {fields.get('Loan.LastModified', 'N/A')}")
        
        return loans
    else:
        print(f"✗ Option 1 failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        # Try option 2
        print("\nTrying filter with Loan.MS.CurrentMilestone...")
        response = requests.post(url, json=payload_option2, headers=headers, timeout=60)
        
        if response.status_code == 200:
            loans = response.json()
            print(f"\n✓ Found {len(loans)} loans in milestone '{milestone_name}'")
            return loans
        else:
            print(f"✗ Option 2 also failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            print("\nPlease run get_pipeline_field_definitions() first to find the correct canonical name.")
            return None


def get_loans_in_dd_requested_queue(limit: int = 100):
    """Convenience function to get loans in 'DD Requested' queue.
    
    This is specifically for the Disclosure Desk workflow where loans are
    waiting for Initial Disclosure (LE) to be sent.
    
    Args:
        limit: Maximum number of loans to return
    
    Returns:
        List of loan dictionaries
    """
    # Common milestone names that might indicate "DD Requested":
    # - "DD Requested"
    # - "Disclosure Requested"
    # - "Doc Preparation"
    # - "Processing"
    
    # Try "DD Requested" first
    loans = get_loans_by_milestone("DD Requested", limit)
    
    if not loans:
        # If that doesn't work, try other common names
        print("\n'DD Requested' not found. Trying 'Doc Preparation'...")
        loans = get_loans_by_milestone("Doc Preparation", limit)
    
    return loans


if __name__ == "__main__":
    import sys
    
    print("Loan Pipeline Filter Tool")
    print("=" * 80)
    
    # Step 1: Get available field definitions
    print("\n[STEP 1] Fetching available pipeline field definitions...")
    definitions = get_pipeline_field_definitions()
    
    if not definitions:
        print("\n✗ Failed to fetch field definitions. Check your API credentials.")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("[STEP 2] Now trying to filter loans by milestone...")
    print("=" * 80)
    
    # Step 2: Try to get loans in DD Requested
    # Uncomment and modify the milestone name as needed:
    
    # loans = get_loans_by_milestone("Processing")
    # loans = get_loans_by_milestone("Doc Preparation")
    loans = get_loans_in_dd_requested_queue()
    
    if loans:
        print(f"\n{'='*80}")
        print("SUCCESS!")
        print(f"{'='*80}")
        print(f"Retrieved {len(loans)} loans from the pipeline.")
        print("\nYou can now use this same pattern to filter by any milestone.")
    else:
        print(f"\n{'='*80}")
        print("NEXT STEPS:")
        print(f"{'='*80}")
        print("1. Check 'pipeline_field_definitions.json' for the correct milestone field")
        print("2. Update the canonicalName in get_loans_by_milestone()")
        print("3. Make sure the milestone name matches exactly (case-sensitive)")



