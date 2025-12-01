"""Test OAuth2 authentication with Encompass API.

This script demonstrates the OAuth2 token generation using client credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from auth import get_access_token, get_auth_manager

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def test_client_credentials_flow():
    """Test OAuth2 client credentials flow."""
    print("=" * 80)
    print("TESTING OAUTH2 CLIENT CREDENTIALS FLOW")
    print("=" * 80)
    print()
    
    # Check required credentials
    print("Checking credentials...")
    client_id = os.getenv("ENCOMPASS_CLIENT_ID")
    client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
    instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
    
    print(f"✓ ENCOMPASS_CLIENT_ID: {client_id[:8]}..." if client_id else "✗ ENCOMPASS_CLIENT_ID: Not set")
    print(f"✓ ENCOMPASS_CLIENT_SECRET: {client_secret[:8]}..." if client_secret else "✗ ENCOMPASS_CLIENT_SECRET: Not set")
    print(f"✓ ENCOMPASS_INSTANCE_ID: {instance_id}" if instance_id else "✗ ENCOMPASS_INSTANCE_ID: Not set")
    print()
    
    if not all([client_id, client_secret, instance_id]):
        print("❌ Missing required credentials. Please set in .env file:")
        print("   ENCOMPASS_CLIENT_ID=your_client_id")
        print("   ENCOMPASS_CLIENT_SECRET=your_client_secret")
        print("   ENCOMPASS_INSTANCE_ID=your_instance_id")
        return False
    
    # Generate OAuth2 token
    print("-" * 80)
    print("Generating OAuth2 token...")
    print()
    
    try:
        # Get token using client credentials flow
        token = get_access_token()
        
        print("✅ Token generated successfully!")
        print()
        print(f"Access Token: {token[:20]}...{token[-10:]}")
        print(f"Token Length: {len(token)} characters")
        print()
        
        # Get token info from auth manager
        auth_manager = get_auth_manager()
        token_info = auth_manager._tokens.get("client_credentials")
        
        if token_info:
            import time
            expires_in = int(token_info.expires_at - time.time())
            print(f"Token Type: {token_info.token_type}")
            print(f"Scope: {token_info.scope}")
            print(f"Expires In: {expires_in} seconds ({expires_in // 60} minutes)")
        
        print()
        print("=" * 80)
        print("✅ AUTHENTICATION SUCCESSFUL")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        print()
        print("Possible issues:")
        print("1. Invalid client_id or client_secret")
        print("2. Instance_id doesn't match your credentials")
        print("3. Network connectivity issues")
        print("4. Encompass API endpoint unreachable")
        print()
        return False


def test_token_caching():
    """Test that tokens are cached and reused."""
    print()
    print("=" * 80)
    print("TESTING TOKEN CACHING")
    print("=" * 80)
    print()
    
    auth_manager = get_auth_manager()
    
    # Clear cache
    auth_manager.clear_cache()
    print("1. Cache cleared")
    
    # First request - should generate new token
    print("2. First request (should generate new token)...")
    token1 = auth_manager.get_token()
    print(f"   Token: {token1[:20]}...")
    
    # Second request - should use cached token
    print("3. Second request (should use cached token)...")
    token2 = auth_manager.get_token()
    print(f"   Token: {token2[:20]}...")
    
    if token1 == token2:
        print()
        print("✅ Token caching works! Same token returned.")
    else:
        print()
        print("⚠️  Different tokens returned (may indicate issue)")
    
    # Force refresh
    print("4. Force refresh (should generate new token)...")
    token3 = auth_manager.get_token(force_refresh=True)
    print(f"   Token: {token3[:20]}...")
    
    print()
    print("=" * 80)
    print("✅ CACHING TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    success = test_client_credentials_flow()
    
    if success:
        test_token_caching()
    else:
        print()
        print("Fix authentication issues before testing caching.")

