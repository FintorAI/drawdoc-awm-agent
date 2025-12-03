"""Encompass OAuth2 authentication manager.

This module handles OAuth2 token generation and management for Encompass API access.
Supports multiple authentication flows including client credentials and password grant.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


@dataclass
class TokenInfo:
    """OAuth2 token information."""
    access_token: str
    expires_at: float
    token_type: str = "Bearer"
    scope: Optional[str] = None


class EncompassAuthManager:
    """Manages OAuth2 authentication for Encompass API.
    
    This class handles token generation, caching, and automatic refresh
    for various OAuth2 flows supported by Encompass API.
    """
    
    def __init__(
        self,
        api_base_url: str = "https://api.elliemae.com",
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """Initialize the authentication manager.
        
        Args:
            api_base_url: Base URL for Encompass API
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._tokens: Dict[str, TokenInfo] = {}
    
    def _token_endpoint(self) -> str:
        """Get the OAuth2 token endpoint URL."""
        return f"{self.api_base_url}/oauth2/v1/token"
    
    def _request_token(
        self,
        data: Dict[str, Any],
        auth: Optional[requests.auth.AuthBase] = None
    ) -> TokenInfo:
        """Request an OAuth2 token from Encompass.
        
        Args:
            data: Form data for token request
            auth: Optional HTTP authentication
            
        Returns:
            TokenInfo containing access token and metadata
            
        Raises:
            requests.HTTPError: If token request fails
        """
        resp = requests.post(
            self._token_endpoint(),
            data=data,
            auth=auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        j = resp.json()
        
        access_token = j["access_token"]
        expires_in = j.get("expires_in", 3600)
        scope = j.get("scope")
        
        return TokenInfo(
            access_token=access_token,
            expires_at=time.time() + expires_in,
            scope=scope,
            token_type=j.get("token_type", "Bearer"),
        )
    
    def _is_expired(self, token: TokenInfo, margin: int = 30) -> bool:
        """Check if token is expired (with safety margin).
        
        Args:
            token: Token to check
            margin: Safety margin in seconds before actual expiration
            
        Returns:
            True if token is expired or will expire within margin
        """
        return time.time() >= (token.expires_at - margin)
    
    def get_client_credentials_token(self, force_refresh: bool = False) -> TokenInfo:
        """Get access token using client credentials flow.
        
        This is the standard OAuth2 client credentials grant type.
        Uses ENCOMPASS_CLIENT_ID, ENCOMPASS_CLIENT_SECRET, and ENCOMPASS_INSTANCE_ID.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
            
        Returns:
            TokenInfo with valid access token
            
        Raises:
            RuntimeError: If required environment variables are missing
            requests.HTTPError: If token request fails
        """
        key = "client_credentials"
        if not force_refresh and key in self._tokens and not self._is_expired(self._tokens[key]):
            return self._tokens[key]
        
        client_id = os.getenv("ENCOMPASS_CLIENT_ID")
        client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
        instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
        scope = os.getenv("ENCOMPASS_SCOPE", "lp")
        
        if not client_id or not client_secret or not instance_id:
            raise RuntimeError(
                "Missing ENCOMPASS_CLIENT_ID/SECRET/INSTANCE_ID for client_credentials flow. "
                "Please set these in your .env file."
            )
        
        data = {
            "grant_type": "client_credentials",
            "instance_id": instance_id,
            "scope": scope,
        }
        
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        token = self._request_token(data=data, auth=auth)
        self._tokens[key] = token
        return token
    
    def get_password_token(self, force_refresh: bool = False) -> TokenInfo:
        """Get access token using password grant flow.
        
        This is the OAuth2 resource owner password credentials grant type.
        Uses ENCOMPASS_USERNAME, ENCOMPASS_PASSWORD, ENCOMPASS_CLIENT_ID, 
        ENCOMPASS_CLIENT_SECRET, and ENCOMPASS_INSTANCE_ID.
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
            
        Returns:
            TokenInfo with valid access token
            
        Raises:
            RuntimeError: If required environment variables are missing
            requests.HTTPError: If token request fails
        """
        key = "password"
        if not force_refresh and key in self._tokens and not self._is_expired(self._tokens[key]):
            return self._tokens[key]
        
        username = os.getenv("ENCOMPASS_USERNAME")
        password = os.getenv("ENCOMPASS_PASSWORD")
        client_id = os.getenv("ENCOMPASS_CLIENT_ID")
        client_secret = os.getenv("ENCOMPASS_CLIENT_SECRET")
        instance_id = os.getenv("ENCOMPASS_INSTANCE_ID")
        scope = os.getenv("ENCOMPASS_SCOPE", "lp")
        
        if not all([username, password, client_id, client_secret, instance_id]):
            raise RuntimeError(
                "Missing credentials for password flow. "
                "Required: ENCOMPASS_USERNAME, ENCOMPASS_PASSWORD, "
                "ENCOMPASS_CLIENT_ID, ENCOMPASS_CLIENT_SECRET, ENCOMPASS_INSTANCE_ID"
            )
        
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "instance_id": instance_id,
            "scope": scope,
        }
        
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        token = self._request_token(data=data, auth=auth)
        self._tokens[key] = token
        return token
    
    def get_token(self, force_refresh: bool = False, use_password: bool = False) -> str:
        """Get a valid access token (simplified interface).
        
        This method automatically chooses the appropriate authentication flow
        based on available credentials:
        - If use_password=True: Uses password grant flow
        - Otherwise: Uses client credentials flow
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
            use_password: Use password grant instead of client credentials
            
        Returns:
            Valid access token string
            
        Raises:
            RuntimeError: If required credentials are missing
            requests.HTTPError: If token request fails
        """
        if use_password:
            return self.get_password_token(force_refresh).access_token
        else:
            return self.get_client_credentials_token(force_refresh).access_token
    
    def clear_cache(self):
        """Clear all cached tokens."""
        self._tokens.clear()


# Global auth manager instance
_auth_manager: Optional[EncompassAuthManager] = None


def get_auth_manager(force_new: bool = False) -> EncompassAuthManager:
    """Get the global authentication manager instance.
    
    Args:
        force_new: If True, create a new manager even if one exists (re-reads .env)
    
    Returns:
        Singleton EncompassAuthManager instance
    """
    global _auth_manager
    if _auth_manager is None or force_new:
        api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
        _auth_manager = EncompassAuthManager(api_base_url=api_base_url)
    return _auth_manager


def reset_auth_manager():
    """Reset the global auth manager (re-reads .env on next call)."""
    global _auth_manager
    _auth_manager = None


def get_access_token(force_refresh: bool = False, use_password: bool = False) -> str:
    """Get a valid Encompass access token (convenience function).
    
    This is the simplest way to get an access token. It handles token
    generation, caching, and automatic refresh.
    
    Args:
        force_refresh: Force token refresh even if cached token is valid
        use_password: Use password grant instead of client credentials
        
    Returns:
        Valid access token string
        
    Raises:
        RuntimeError: If required credentials are missing
        requests.HTTPError: If token request fails
        
    Example:
        >>> token = get_access_token()
        >>> headers = {"Authorization": f"Bearer {token}"}
    """
    return get_auth_manager().get_token(force_refresh, use_password)

