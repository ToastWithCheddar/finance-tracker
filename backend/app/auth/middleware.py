from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from typing import Optional

from app.auth.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication for protected routes"""
    
    def __init__(self, app, protected_paths: Optional[list] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/api/users/me",
            "/api/transactions",
            "/api/budgets",
            "/api/goals",
            "/api/accounts",
            "/api/insights",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for non-protected paths
        if not self._is_protected_path(request.url.path):
            return await call_next(request)
        
        # Get authorization header
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() != "bearer":
            return Response(
                content="Missing or invalid authentication token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token
        try:
            user_data = await supabase_client.verify_token(credentials)
            if not user_data:
                return Response(
                    content="Invalid authentication token",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add user data to request state
            request.state.user = user_data
            
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return Response(
                content="Authentication failed",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires authentication"""
        return any(path.startswith(protected) for protected in self.protected_paths)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next):
        # Simple rate limiting based on IP
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        minute_ago = current_time - 60
        self.request_counts = {
            ip: [(timestamp, count) for timestamp, count in requests if timestamp > minute_ago]
            for ip, requests in self.request_counts.items()
        }
        
        # Check current requests
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        recent_requests = len(self.request_counts[client_ip])
        if recent_requests >= self.requests_per_minute:
            return Response(
                content="Rate limit exceeded",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
            )
        
        # Add current request
        self.request_counts[client_ip].append((current_time, 1))
        
        return await call_next(request)