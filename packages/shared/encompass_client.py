"""Shared Encompass client utility for all agents."""

import os
from pathlib import Path
from copilotagent import EncompassConnect
from dotenv import load_dotenv
from .auth import get_access_token

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def get_encompass_client(auto_generate_token: bool = True, use_password: bool = False) -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables.
    
    This function loads credentials from environment variables and returns
    a configured EncompassConnect client that can be used across all agents.
    
    Authentication Methods:
    1. Auto-generate token (default): Uses OAuth2 client credentials flow
       - Requires: ENCOMPASS_CLIENT_ID, ENCOMPASS_CLIENT_SECRET, ENCOMPASS_INSTANCE_ID
       - Automatically generates and caches access token
       - Tokens are auto-refreshed when expired
    
    2. Manual token: Uses pre-generated access token from env var
       - Requires: ENCOMPASS_ACCESS_TOKEN
       - Set auto_generate_token=False
    
    3. Password flow: Uses username/password with client credentials
       - Requires: All credentials including USERNAME and PASSWORD
       - Set use_password=True
    
    Environment variables:
    - ENCOMPASS_CLIENT_ID: OAuth2 client ID
    - ENCOMPASS_CLIENT_SECRET: OAuth2 client secret
    - ENCOMPASS_INSTANCE_ID: Encompass instance ID
    - ENCOMPASS_ACCESS_TOKEN: Pre-generated token (optional if auto_generate_token=True)
    - ENCOMPASS_API_BASE_URL: API base URL (optional, defaults to https://api.elliemae.com)
    - ENCOMPASS_USERNAME: User login (required for password flow)
    - ENCOMPASS_PASSWORD: User password (required for password flow)
    - ENCOMPASS_SUBJECT_USER_ID: Subject user ID (optional)
    - ENCOMPASS_SCOPE: OAuth2 scope (optional, defaults to "lp")
    - LANDINGAI_API_KEY: LandingAI API key (optional)
    
    Args:
        auto_generate_token: If True, automatically generate OAuth2 token from client credentials.
                           If False, use ENCOMPASS_ACCESS_TOKEN from env var.
        use_password: If True, use password grant flow instead of client credentials.
                     Only applies when auto_generate_token=True.
    
    Returns:
        EncompassConnect: Configured Encompass client with valid authentication
        
    Raises:
        RuntimeError: If required credentials are missing
        requests.HTTPError: If token generation fails (when auto_generate_token=True)
    
    Examples:
        # Auto-generate token from client credentials (recommended)
        >>> client = get_encompass_client()
        
        # Use manual token from env var
        >>> client = get_encompass_client(auto_generate_token=False)
        
        # Use password flow
        >>> client = get_encompass_client(use_password=True)
    """
    # Get or generate access token
    if auto_generate_token:
        # Generate OAuth2 token from client credentials or password
        access_token = get_access_token(use_password=use_password)
    else:
        # Use pre-generated token from env var
        access_token = os.getenv("ENCOMPASS_ACCESS_TOKEN", "")
        if not access_token:
            raise RuntimeError(
                "ENCOMPASS_ACCESS_TOKEN not set. Either:\n"
                "1. Set ENCOMPASS_ACCESS_TOKEN in .env, or\n"
                "2. Use auto_generate_token=True (default) with CLIENT_ID/SECRET/INSTANCE_ID"
            )
    
    # Get other configuration
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    # Build credentials dict for EncompassConnect
    # Note: EncompassConnect requires all credential fields even when using OAuth2
    credentials = {
        "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
        "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
        "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
        "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        "username": os.getenv("ENCOMPASS_USERNAME", ""),
        "password": os.getenv("ENCOMPASS_PASSWORD", ""),
    }
    
    return EncompassConnect(
        access_token=access_token,
        api_base_url=api_base_url,
        credentials=credentials,
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )

