"""Google OAuth2 authentication"""
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from clawbot.config import settings
from clawbot.auth.token_cache import token_cache


class GoogleOAuth:
    """Handles Google OAuth2 authentication flow"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = settings.GOOGLE_SCOPES.split()
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError(
                "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI "
                "must be set in environment variables"
            )
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate authorization URL for OAuth flow"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return authorization_url
    
    def exchange_code_for_token(
        self, 
        authorization_code: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials
        
        # Prepare token data for caching
        now = datetime.now(timezone.utc)
        expiry = credentials.expiry
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'expires_at': expiry.timestamp() if expiry else None,
            'expires_in': int((expiry - now).total_seconds()) if expiry else None,
        }
        
        # Cache the token
        token_cache.set_token(user_id, token_data)
        
        return token_data
    
    def refresh_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        cached_token = token_cache.get_token(user_id)
        if not cached_token:
            return None
        
        # Create credentials object from cached token
        credentials = Credentials(
            token=cached_token.get('token'),
            refresh_token=cached_token.get('refresh_token'),
            token_uri=cached_token.get('token_uri'),
            client_id=cached_token.get('client_id'),
            client_secret=cached_token.get('client_secret'),
            scopes=cached_token.get('scopes')
        )
        
        # Refresh if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # Update cached token
            now = datetime.now(timezone.utc)
            expiry = credentials.expiry
            if expiry and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes) if credentials.scopes else [],
                'expires_at': expiry.timestamp() if expiry else None,
                'expires_in': int((expiry - now).total_seconds()) if expiry else None,
            }
            
            token_cache.set_token(user_id, token_data)
            return token_data
        
        return cached_token


def get_google_credentials(user_id: str) -> Optional[Credentials]:
    """Get valid Google credentials for a user"""
    cached_token = token_cache.get_token(user_id)
    
    if not cached_token:
        return None
    
    # Check if token is valid
    if not token_cache.is_token_valid(cached_token):
        # Try to refresh
        oauth = GoogleOAuth()
        refreshed = oauth.refresh_token(user_id)
        if not refreshed:
            return None
        cached_token = refreshed
    
    # Create credentials object
    credentials = Credentials(
        token=cached_token.get('token'),
        refresh_token=cached_token.get('refresh_token'),
        token_uri=cached_token.get('token_uri'),
        client_id=cached_token.get('client_id'),
        client_secret=cached_token.get('client_secret'),
        scopes=cached_token.get('scopes')
    )
    
    return credentials
