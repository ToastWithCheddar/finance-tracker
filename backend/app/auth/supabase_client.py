from supabase import create_client, Client
from gotrue.errors import AuthError
from app.config import settings
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            logger.warning("Supabase credentials not configured")
            self._client = None
            self._configured = False
        else:
            try:
                self._client: Client = create_client(
                    settings.SUPABASE_URL, 
                    settings.SUPABASE_ANON_KEY
                )
                self._configured = True
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self._client = None
                self._configured = False
    
    @property
    def client(self) -> Client:
        if not self._configured:
            raise ValueError("Supabase client not configured")
        return self._client
    
    def is_configured(self) -> bool:
        return self._configured
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token with Supabase"""
        if not self.is_configured():
            return None
            
        try:
            response = self.client.auth.get_user(token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "email_verified": response.user.email_confirmed_at is not None,
                    "metadata": response.user.user_metadata,
                }
            return None
        except AuthError as e:
            logger.error(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None

# Global instance
supabase_client = SupabaseClient()