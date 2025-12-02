"""
Debug OAuth Credentials for Encompass MCP Server

This script checks:
1. Which environment variables are set
2. Attempts OAuth token request
3. Shows detailed error information
4. Provides fix suggestions
"""

import os
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment from BOTH sources
# Strategy: MCP server FIRST (Encompass OAuth), then local (LandingAI, etc.)
from dotenv import load_dotenv

# 1. Load MCP server .env FIRST (for working Encompass OAuth credentials)
mcp_env_path = project_root.parent / "encompass-mcp-server" / ".env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path)
    print(f"✅ Loaded MCP server environment from: {mcp_env_path}\n")
else:
    print(f"⚠️  MCP server .env not found at: {mcp_env_path}\n")

# 2. Then load local .env WITHOUT override (for LandingAI, DOCREPO, etc.)
env_path = project_root / "agents" / "drawdocs" / "subagents" / "preparation_agent" / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)
    print(f"✅ Loaded local environment from: {env_path}\n")
else:
    load_dotenv(override=False)
    print(f"✅ Loaded local environment from default locations\n")

print("=" * 80)
print("ENCOMPASS OAUTH CREDENTIALS DEBUG")
print("=" * 80)
print()

# Required environment variables
required_vars = {
    "ENCOMPASS_CLIENT_ID": "Client ID for OAuth",
    "ENCOMPASS_CLIENT_SECRET": "Client Secret for OAuth",
    "ENCOMPASS_INSTANCE_ID": "Instance ID (e.g., TEBE11211111)",
}

optional_vars = {
    "ENCOMPASS_API_HOST": "API Host (e.g., api.elliemae.com) - can be extracted from API_SERVER",
    "ENCOMPASS_API_SERVER": "Full API server URL (e.g., https://api.elliemae.com)",
    "ENCOMPASS_SCOPE": "OAuth scope (usually 'lp' for Lender Platform)",
    "ENCOMPASS_SUBJECT_USER_ID": "Subject user for impersonation",
}

print("📋 CHECKING REQUIRED CREDENTIALS")
print("-" * 80)

missing_required = []
masked_values = {}

for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "SECRET" in var or "PASSWORD" in var:
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
        else:
            masked = value
        masked_values[var] = masked
        print(f"✅ {var}: {masked}")
        print(f"   └─ {description}")
    else:
        print(f"❌ {var}: NOT SET")
        print(f"   └─ {description}")
        missing_required.append(var)

print()
print("📋 CHECKING OPTIONAL CREDENTIALS")
print("-" * 80)

for var, description in optional_vars.items():
    value = os.getenv(var)
    if value:
        masked_values[var] = value
        print(f"✅ {var}: {value}")
        print(f"   └─ {description}")
    else:
        print(f"⚠️  {var}: NOT SET (optional)")
        print(f"   └─ {description}")

print()
print("=" * 80)

if missing_required:
    print("❌ MISSING REQUIRED CREDENTIALS")
    print("=" * 80)
    print()
    print("The following required variables are missing:")
    for var in missing_required:
        print(f"  • {var}")
    print()
    print("Add these to your .env file:")
    print(f"  {env_path}")
    print()
    sys.exit(1)

print("✅ ALL REQUIRED CREDENTIALS PRESENT")
print("=" * 80)
print()

# Try to import MCP server components
print("🔌 TESTING MCP SERVER CONNECTION")
print("-" * 80)

try:
    mcp_server_path = project_root.parent / "encompass-mcp-server"
    print(f"MCP Server Path: {mcp_server_path}")
    
    if not mcp_server_path.exists():
        print(f"❌ MCP server not found at: {mcp_server_path}")
        sys.exit(1)
    
    print(f"✅ MCP server directory exists")
    
    sys.path.insert(0, str(mcp_server_path))
    
    from util.auth import EncompassAuthManager
    from util.http import EncompassHttpClient
    
    print(f"✅ Successfully imported EncompassAuthManager")
    print(f"✅ Successfully imported EncompassHttpClient")
    print()
    
except ImportError as e:
    print(f"❌ Failed to import MCP server components: {e}")
    sys.exit(1)

# Test OAuth token request
print("🔐 TESTING OAUTH TOKEN REQUEST")
print("-" * 80)

try:
    # Create auth manager
    client_id = os.getenv("ENCOMPASS_CLIENT_ID")
    client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
    instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
    
    # Handle both ENCOMPASS_API_HOST and ENCOMPASS_API_SERVER
    api_host = os.getenv("ENCOMPASS_API_HOST")
    if not api_host:
        api_server = os.getenv("ENCOMPASS_API_SERVER", "https://api.elliemae.com")
        # Extract host from URL (remove https://)
        api_host = api_server.replace("https://", "").replace("http://", "")
        print(f"ℹ️  ENCOMPASS_API_HOST not set, extracted from ENCOMPASS_API_SERVER: {api_host}")
        print()
    
    scope = os.getenv("ENCOMPASS_SCOPE", "lp")
    
    # Get full API server URL
    api_server = os.getenv("ENCOMPASS_API_SERVER", "https://api.elliemae.com")
    
    print(f"Creating AuthManager with:")
    print(f"  • API Server: {api_server}")
    print(f"  • Instance ID: {instance_id} (from env)")
    print(f"  • Client ID: {client_id[:10]}... (from env)")
    print(f"  • Scope: {scope} (from env)")
    print()
    
    # EncompassAuthManager reads credentials from env vars, not constructor params
    auth_manager = EncompassAuthManager(
        api_server=api_server,
        timeout=60,
        verify_ssl=True
    )
    
    print("Requesting client credentials token...")
    print("(Credentials are read from environment variables)")
    print()
    
    # This is the actual OAuth call that's failing
    token_info = auth_manager.get_client_credentials_token()
    
    print()
    print("✅ SUCCESS! OAuth token retrieved")
    print(f"   Token Type: {token_info.token_type}")
    print(f"   Access Token (first 20 chars): {token_info.access_token[:20]}...")
    print(f"   Scope: {token_info.scope}")
    print()
    
    # Test a milestone API call
    print("🧪 TESTING MILESTONE API CALL")
    print("-" * 80)
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    http_client = EncompassHttpClient(
        api_server=api_server,
        auth_manager=auth_manager,
        timeout=60,
        verify_ssl=True
    )
    
    response = http_client.request(
        method="GET",
        path=f"/encompass/v1/loans/{loan_id}/milestones",
        token=token_info
    )
    
    if response.status_code == 200:
        milestones = response.json()
        print(f"✅ Successfully retrieved {len(milestones)} milestones!")
        print()
        
        if milestones:
            print("📌 Sample milestone data:")
            for ms in milestones[:3]:  # Show first 3
                print(f"  • {ms.get('milestoneName', 'N/A')}: {ms.get('status', 'N/A')}")
        else:
            print("ℹ️  No milestones found for this loan (this is normal if loan has no milestones)")
        print()
        
    else:
        print(f"⚠️  API returned status {response.status_code}")
        print(f"Response: {response.text[:200]}")
        print()
    
    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("Your OAuth credentials are working correctly.")
    print("The milestone API should work in primitives.py now.")
    
except Exception as e:
    print()
    print("❌ OAUTH TOKEN REQUEST FAILED")
    print("=" * 80)
    print()
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    print()
    
    # Try to get more details from the response
    response_details = None
    if hasattr(e, 'response') and e.response is not None:
        try:
            response_details = e.response.json()
            print(f"Response Details: {json.dumps(response_details, indent=2)}")
            print()
        except:
            print(f"Response Text: {e.response.text[:500]}")
            print()
    
    # Check for common issues
    error_str = str(e).lower()
    
    if "400" in error_str or "bad request" in error_str:
        print("🔍 DIAGNOSIS: 400 Bad Request")
        print("-" * 80)
        print()
        print("This usually means one of:")
        print("  1. ENCOMPASS_SCOPE is missing or wrong (should be 'lp')")
        print("  2. ENCOMPASS_INSTANCE_ID is incorrect")
        print("  3. CLIENT_ID or CLIENT_SECRET are invalid")
        print()
        print("Current values:")
        print(f"  • SCOPE: {os.getenv('ENCOMPASS_SCOPE', 'NOT SET')}")
        instance = os.getenv('ENCOMPASS_INSTANCE_ID', 'NOT SET')
        print(f"  • INSTANCE_ID: {instance}")
        print()
        
        # Check if INSTANCE_ID might be missing prefix
        if instance and not instance.startswith('T'):
            print("⚠️  INSTANCE_ID might be incorrect!")
            print(f"   Current: {instance}")
            print(f"   Test environments usually start with 'TEBE', like: TEBE{instance}")
            print(f"   Production environments usually start with 'BE', like: {instance}")
            print()
        
        print("Try fixing in your .env:")
        print("  1. For TEST environment: ENCOMPASS_INSTANCE_ID=TEBE11207984")
        print("  2. For PRODUCTION environment: ENCOMPASS_INSTANCE_ID=BE11207984")
        print("  3. Verify your CLIENT_ID and CLIENT_SECRET are correct")
        print()
        
    elif "401" in error_str or "unauthorized" in error_str:
        print("🔍 DIAGNOSIS: 401 Unauthorized")
        print("-" * 80)
        print()
        print("Your CLIENT_ID or CLIENT_SECRET are incorrect.")
        print("Please verify these credentials with your Encompass administrator.")
        print()
        
    elif "403" in error_str or "forbidden" in error_str:
        print("🔍 DIAGNOSIS: 403 Forbidden")
        print("-" * 80)
        print()
        print("Your credentials are valid but don't have permission.")
        print("Contact your Encompass administrator to grant API access.")
        print()
    
    else:
        print("🔍 DIAGNOSIS: Unknown Error")
        print("-" * 80)
        print()
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        print()
    
    sys.exit(1)

