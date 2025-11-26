"""Shared Encompass client utility for all agents."""

import os
from copilotagent import EncompassConnect


def get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables.
    
    This function loads credentials from environment variables and returns
    a configured EncompassConnect client that can be used across all agents.
    
    Environment variables required:
    - ENCOMPASS_ACCESS_TOKEN
    - ENCOMPASS_API_BASE_URL (optional, defaults to https://api.elliemae.com)
    - ENCOMPASS_USERNAME
    - ENCOMPASS_PASSWORD
    - ENCOMPASS_CLIENT_ID
    - ENCOMPASS_CLIENT_SECRET
    - ENCOMPASS_INSTANCE_ID
    - ENCOMPASS_SUBJECT_USER_ID
    - LANDINGAI_API_KEY
    
    Returns:
        EncompassConnect: Configured Encompass client
    """
    return EncompassConnect(
        access_token=os.getenv("ENCOMPASS_ACCESS_TOKEN", ""),
        api_base_url=os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com"),
        credentials={
            "username": os.getenv("ENCOMPASS_USERNAME", ""),
            "password": os.getenv("ENCOMPASS_PASSWORD", ""),
            "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
            "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
            "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
            "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        },
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )

