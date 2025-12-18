"""
Get all loans in specific Disclosure Desk (DD) queues/pipeline folders.

DD Queues:
1. DD Request - Initial disclosure requests
2. DD Corrections - Corrections needed
3. DD Approved to Send - Ready to send
4. DD LO To Review / Corrections Needed - LO review queue
5. DD Locked Loans - Locked loans awaiting disclosure

DrawDocs starts at: "Closing - Docs Ordered" milestone
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_encompass_token() -> Tuple[str, str]:
    """Get OAuth2 token for Encompass API.
    
    Returns:
        Tuple of (access_token, base_url)
    """
    # Use regular ENCOMPASS credentials
    base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    client_id = os.getenv("ENCOMPASS_CLIENT_ID")
    client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
    instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
    
    token_url = f"{base_url}/oauth2/v1/token"
    
    # Try client_credentials first
    payload = {
        "grant_type": "client_credentials",
        "instance_id": instance_id,
        "scope": "lp",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    # Use form-encoded data (not JSON) for OAuth token request
    response = requests.post(token_url, data=payload)
    
    # If client_credentials fails, try password grant
    if not response.ok and "username & password" in response.text.lower():
        username = os.getenv("ENCOMPASS_SUBJECT_USER_ID")
        password = os.getenv("ENCOMPASS_PASSWORD")
        
        if username and password:
            payload = {
                "grant_type": "password",
                "username": f"{username}@encompass:{instance_id}",
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "lp"
            }
            response = requests.post(token_url, data=payload)
    
    if not response.ok:
        print(f"   ❌ Authentication error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    return response.json()["access_token"], base_url


# =============================================================================
# DD QUEUE NAMES
# =============================================================================

DD_QUEUES = {
    "DD_REQUEST": "DD Request",
    "DD_CORRECTIONS": "DD Corrections", 
    "DD_APPROVED_TO_SEND": "DD Approved to Send",
    "DD_LO_REVIEW": "DD LO To Review / Corrections Needed",
    "DD_LOCKED_LOANS": "DD Locked Loans",
}

# DrawDocs milestone
DRAWDOCS_MILESTONE = "Closing - Docs Ordered"


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_loans_in_dd_queue(queue_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all loans in a specific DD queue/pipeline folder.
    
    Args:
        queue_name: Name of the DD queue (e.g., "DD Request")
        limit: Maximum number of loans to return (default 100, max 25000)
    
    Returns:
        List of loan dictionaries with GUIDs and field data
    """
    token, api_base = get_encompass_token()
    
    url = f"{api_base}/encompass/v1/loanPipeline?limit={limit}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Filter by Loan.LoanFolder (pipeline folder/queue name)
    payload = {
        "filter": {
            "canonicalName": "Loan.LoanFolder",
            "value": queue_name,
            "matchType": "exact"
        },
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",  # Borrower First Name
            "Fields.5",  # Borrower Last Name
            "Fields.11",  # Loan Amount
            "Fields.1393",  # Loan Status
            "Fields.1987",  # Current Milestone
            "Fields.745",  # Application Date
            "Loan.LastModified"
        ],
        "sortOrder": [
            {
                "canonicalName": "Loan.LastModified",
                "order": "desc"  # Most recent first
            }
        ]
    }
    
    print(f"\n{'='*80}")
    print(f"SEARCHING FOR LOANS IN QUEUE: {queue_name}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            loans = response.json()
            print(f"✓ Found {len(loans)} loans in '{queue_name}' queue")
            
            # Display results
            if loans:
                print(f"\n{'='*80}")
                print(f"LOANS IN '{queue_name}' QUEUE:")
                print(f"{'='*80}\n")
                
                for idx, loan in enumerate(loans, 1):
                    loan_guid = loan.get('loanGuid')
                    fields = loan.get('fields', {})
                    
                    borrower_first = fields.get('Fields.4', '')
                    borrower_last = fields.get('Fields.5', '')
                    borrower_name = f"{borrower_first} {borrower_last}".strip()
                    
                    print(f"{idx}. Loan {loan_guid[:8]}...")
                    print(f"   Loan Number: {fields.get('Loan.LoanNumber', 'N/A')}")
                    print(f"   Borrower: {borrower_name or 'N/A'}")
                    print(f"   Amount: ${fields.get('Fields.11', 'N/A')}")
                    print(f"   Status: {fields.get('Fields.1393', 'N/A')}")
                    print(f"   Milestone: {fields.get('Fields.1987', 'N/A')}")
                    print(f"   Last Modified: {fields.get('Loan.LastModified', 'N/A')}")
                    print()
            
            return loans
        else:
            print(f"✗ Request failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_loans_by_drawdocs_milestone(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all loans in the DrawDocs starting milestone.
    
    DrawDocs starts at: "Closing - Docs Ordered"
    
    Args:
        limit: Maximum number of loans to return
    
    Returns:
        List of loan dictionaries
    """
    token, api_base = get_encompass_token()
    
    url = f"{api_base}/encompass/v1/loanPipeline?limit={limit}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Filter by Current Milestone (Field 1987)
    payload = {
        "filter": {
            "canonicalName": "Fields.1987",
            "value": DRAWDOCS_MILESTONE,
            "matchType": "exact"
        },
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",
            "Fields.5",
            "Fields.11",
            "Fields.1393",
            "Fields.1987",
            "Loan.LastModified"
        ]
    }
    
    print(f"\n{'='*80}")
    print(f"SEARCHING FOR LOANS IN MILESTONE: {DRAWDOCS_MILESTONE}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            loans = response.json()
            print(f"✓ Found {len(loans)} loans in '{DRAWDOCS_MILESTONE}' milestone")
            return loans
        else:
            print(f"✗ Request failed: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def get_all_dd_queues_summary(limit_per_queue: int = 10) -> Dict[str, List[Dict]]:
    """Get a summary of all DD queues and their loan counts.
    
    Args:
        limit_per_queue: Number of loans to retrieve per queue
    
    Returns:
        Dictionary mapping queue names to loan lists
    """
    results = {}
    
    print(f"\n{'='*80}")
    print("DISCLOSURE DESK QUEUES SUMMARY")
    print(f"{'='*80}\n")
    
    for queue_key, queue_name in DD_QUEUES.items():
        print(f"\nFetching {queue_name}...")
        loans = get_loans_in_dd_queue(queue_name, limit=limit_per_queue)
        results[queue_name] = loans
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    
    total_loans = 0
    for queue_name, loans in results.items():
        count = len(loans)
        total_loans += count
        status = "✓" if count > 0 else "○"
        print(f"{status} {queue_name:45} {count:3} loans")
    
    print(f"\n{'='*80}")
    print(f"TOTAL LOANS ACROSS ALL DD QUEUES: {total_loans}")
    print(f"{'='*80}\n")
    
    return results


def filter_loans_with_multiple_criteria(
    queue_name: str = None,
    milestone: str = None,
    loan_status: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Filter loans with multiple criteria.
    
    Example: Get loans in "DD Request" queue that are also in "Processing" milestone
    
    Args:
        queue_name: Loan folder/queue name (e.g., "DD Request")
        milestone: Current milestone (e.g., "Processing")
        loan_status: Loan status (e.g., "Active")
        limit: Maximum number of loans to return
    
    Returns:
        List of loan dictionaries
    """
    token, api_base = get_encompass_token()
    
    url = f"{api_base}/encompass/v1/loanPipeline?limit={limit}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Build filter criteria
    filter_terms = []
    
    if queue_name:
        filter_terms.append({
            "canonicalName": "Loan.LoanFolder",
            "value": queue_name,
            "matchType": "exact"
        })
    
    if milestone:
        filter_terms.append({
            "canonicalName": "Fields.1987",
            "value": milestone,
            "matchType": "exact"
        })
    
    if loan_status:
        filter_terms.append({
            "canonicalName": "Fields.1393",
            "value": loan_status,
            "matchType": "exact"
        })
    
    # If only one filter, use simple structure; if multiple, use terms/operator
    if len(filter_terms) == 1:
        filter_obj = filter_terms[0]
    elif len(filter_terms) > 1:
        filter_obj = {
            "operator": "and",
            "terms": filter_terms
        }
    else:
        filter_obj = {}
    
    payload = {
        "filter": filter_obj,
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",
            "Fields.5",
            "Fields.1393",
            "Fields.1987",
            "Loan.LastModified"
        ]
    }
    
    print(f"\n{'='*80}")
    print("FILTERING LOANS WITH CRITERIA:")
    if queue_name:
        print(f"  Queue: {queue_name}")
    if milestone:
        print(f"  Milestone: {milestone}")
    if loan_status:
        print(f"  Status: {loan_status}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            loans = response.json()
            print(f"✓ Found {len(loans)} matching loans")
            return loans
        else:
            print(f"✗ Request failed: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys
    import json
    
    print("\n" + "="*80)
    print("DISCLOSURE DESK QUEUE FILTER TOOL")
    print("="*80)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "dd-request":
            # Get loans in DD Request queue
            loans = get_loans_in_dd_queue(DD_QUEUES["DD_REQUEST"])
            
        elif command == "dd-corrections":
            # Get loans in DD Corrections queue
            loans = get_loans_in_dd_queue(DD_QUEUES["DD_CORRECTIONS"])
            
        elif command == "dd-approved":
            # Get loans in DD Approved to Send queue
            loans = get_loans_in_dd_queue(DD_QUEUES["DD_APPROVED_TO_SEND"])
            
        elif command == "dd-lo-review":
            # Get loans in DD LO Review queue
            loans = get_loans_in_dd_queue(DD_QUEUES["DD_LO_REVIEW"])
            
        elif command == "dd-locked":
            # Get loans in DD Locked Loans queue
            loans = get_loans_in_dd_queue(DD_QUEUES["DD_LOCKED_LOANS"])
            
        elif command == "drawdocs":
            # Get loans in DrawDocs milestone
            loans = get_loans_by_drawdocs_milestone()
            
        elif command == "summary":
            # Get summary of all DD queues
            results = get_all_dd_queues_summary()
            
        elif command == "help":
            print("\nUsage:")
            print("  python get_loans_by_dd_queue.py [command]")
            print("\nCommands:")
            print("  dd-request      - Get loans in 'DD Request' queue")
            print("  dd-corrections  - Get loans in 'DD Corrections' queue")
            print("  dd-approved     - Get loans in 'DD Approved to Send' queue")
            print("  dd-lo-review    - Get loans in 'DD LO Review' queue")
            print("  dd-locked       - Get loans in 'DD Locked Loans' queue")
            print("  drawdocs        - Get loans in 'Closing - Docs Ordered' milestone")
            print("  summary         - Get summary of all DD queues")
            print("  help            - Show this help message")
            
        else:
            print(f"\n✗ Unknown command: {command}")
            print("Run with 'help' for usage information")
    
    else:
        # Default: Show summary of all DD queues
        print("\nNo command specified. Showing summary of all DD queues...")
        print("(Run with 'help' for more options)\n")
        
        results = get_all_dd_queues_summary()
        
        # Save to file
        output_file = "dd_queues_summary.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")

