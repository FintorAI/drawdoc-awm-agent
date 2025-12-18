"""
Discover what loan folders/queues actually exist in your Encompass system.
This will help identify the exact folder names to use for filtering.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple
from collections import Counter

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def get_encompass_token() -> Tuple[str, str]:
    """Get OAuth2 token for Encompass API."""
    base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    client_id = os.getenv("ENCOMPASS_CLIENT_ID")
    client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
    instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
    
    token_url = f"{base_url}/oauth2/v1/token"
    
    payload = {
        "grant_type": "client_credentials",
        "instance_id": instance_id,
        "scope": "lp",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    response = requests.post(token_url, data=payload)
    
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
        print(f"❌ Authentication error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    return response.json()["access_token"], base_url


def get_all_loans_with_folders(limit: int = 500):
    """Get all loans and their folder names to discover what folders exist."""
    
    token, api_base = get_encompass_token()
    
    url = f"{api_base}/encompass/v1/loanPipeline?limit={limit}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Get all loans with their folders (no filter)
    payload = {
        "fields": [
            "Loan.LoanNumber",
            "Loan.LoanFolder",
            "Fields.4",  # Borrower First Name
            "Fields.1393",  # Loan Status
            "Fields.1987",  # Current Milestone
            "Loan.LastModified"
        ]
    }
    
    print(f"\n{'='*80}")
    print(f"DISCOVERING LOAN FOLDERS IN YOUR ENCOMPASS SYSTEM")
    print(f"{'='*80}\n")
    print(f"Fetching up to {limit} loans...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            loans = response.json()
            print(f"✓ Found {len(loans)} total loans\n")
            
            if not loans:
                print("⚠️  No loans found in the system.")
                return
            
            # Count loans by folder
            folder_counts = Counter()
            milestone_counts = Counter()
            folder_loans = {}
            
            for loan in loans:
                fields = loan.get('fields', {})
                folder = fields.get('Loan.LoanFolder', 'No Folder')
                milestone = fields.get('Fields.1987', 'No Milestone')
                
                folder_counts[folder] += 1
                milestone_counts[milestone] += 1
                
                if folder not in folder_loans:
                    folder_loans[folder] = []
                folder_loans[folder].append(loan)
            
            # Display folders
            print(f"{'='*80}")
            print(f"LOAN FOLDERS (QUEUES) FOUND:")
            print(f"{'='*80}\n")
            
            for folder, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
                print(f"📁 {folder:50} {count:3} loans")
            
            # Display milestones
            print(f"\n{'='*80}")
            print(f"MILESTONES FOUND:")
            print(f"{'='*80}\n")
            
            for milestone, count in sorted(milestone_counts.items(), key=lambda x: -x[1]):
                print(f"🏁 {milestone:50} {count:3} loans")
            
            # Show sample loans from folders that might be DD-related
            print(f"\n{'='*80}")
            print(f"SAMPLE LOANS FROM KEY FOLDERS:")
            print(f"{'='*80}\n")
            
            dd_keywords = ['dd', 'disclosure', 'draw', 'doc', 'closing']
            
            for folder, loans_in_folder in sorted(folder_loans.items()):
                # Check if folder name contains any DD-related keywords
                folder_lower = folder.lower()
                if any(keyword in folder_lower for keyword in dd_keywords) or len(folder_loans) <= 10:
                    print(f"\n📁 Folder: '{folder}' ({len(loans_in_folder)} loans)")
                    
                    # Show first 3 loans as examples
                    for loan in loans_in_folder[:3]:
                        loan_guid = loan.get('loanGuid')
                        fields = loan.get('fields', {})
                        print(f"   • Loan {loan_guid[:8]}... | {fields.get('Loan.LoanNumber', 'N/A')} | {fields.get('Fields.4', 'N/A')} | Status: {fields.get('Fields.1393', 'N/A')}")
            
            # Save results to file
            import json
            output = {
                "total_loans": len(loans),
                "folders": dict(folder_counts),
                "milestones": dict(milestone_counts),
                "sample_loans": loans[:50]  # Save first 50 for reference
            }
            
            with open('loan_folders_discovery.json', 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\n{'='*80}")
            print(f"✓ Results saved to: loan_folders_discovery.json")
            print(f"{'='*80}\n")
            
            # Provide suggestions
            print(f"\n{'='*80}")
            print(f"NEXT STEPS:")
            print(f"{'='*80}\n")
            print("1. Look at the folder names above to find your DD queues")
            print("2. Update DD_QUEUES in get_loans_by_dd_queue.py with the exact names")
            print("3. Folder names are CASE-SENSITIVE and must match exactly")
            print("\nExample:")
            print("  If you see '📁 Disclosure Request', use that instead of 'DD Request'")
            
        else:
            print(f"✗ Request failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    get_all_loans_with_folders()



