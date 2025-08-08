from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import logging

# New import for on-the-fly user creation
from app.schemas.user import UserCreate

from app.database import get_db
from app.auth.supabase_client import supabase_client
from app.services.user_service import UserService
from app.models.user import User
from app.auth.auth_service import AuthService
from app.utils.security import verify_token

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get the authentication service."""
    return AuthService(db)

# TODO: try except blocks are too broad, we should be more specific about the errors we are catching
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Gets the current authenticated user from a token."""
    token = credentials.credentials
    
    # Development mode: accept mock tokens
    from app.config import settings
    if hasattr(settings, 'ENVIRONMENT') and settings.ENVIRONMENT == 'development':
        if token.startswith('dev-mock-token-'):
            # Return or create a development user
            dev_user = auth_service.user_service.get_by_email(
                db=auth_service.db,
                email='dev@example.com'
            )
            
            if not dev_user:
                from uuid import uuid4
                dev_user = auth_service.user_service.create(
                    db=auth_service.db,
                    obj_in=UserCreate(
                        email='dev@example.com',
                        display_name='Development User',
                        first_name='Dev',
                        last_name='User',
                        supabase_user_id=uuid4(),
                        is_verified=True,
                        is_active=True
                    )
                )
            
            return dev_user
    
    try:
        # First, try to verify as our custom JWT token (from magic link flow)
        custom_payload = verify_token(token)
        if custom_payload and custom_payload.get('user_id'):
            # This is a custom JWT token - get user directly by ID
            user = auth_service.user_service.get(
                db=auth_service.db,
                id=custom_payload['user_id']
            )
            if user and user.is_active:
                return user
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
        
        # If not a custom JWT, try Supabase token validation
        user_data = auth_service.supabase.client.auth.get_user(token)
        if not user_data or not user_data.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        
        # Try to fetch matching local user row
        user = auth_service.user_service.get_by_supabase_id(
            db=auth_service.db,
            supabase_user_id=uuid.UUID(user_data.user.id)
        )

        # Automatically provision a local record if it doesn't exist (first login from older account)
        if not user:
            uid = uuid.UUID(user_data.user.id)

            # Check if a local user exists with the same e-mail (created earlier without UID)
            existing_by_email = auth_service.user_service.get_by_email(
                db=auth_service.db,
                email=user_data.user.email,
            )

            if existing_by_email:
                # Link the Supabase UID to that user and update verification flag
                try:
                    existing_by_email.supabase_user_id = uid
                    existing_by_email.is_verified = user_data.user.email_confirmed_at is not None
                    auth_service.db.add(existing_by_email)
                    auth_service.db.commit()
                    auth_service.db.refresh(existing_by_email)
                    user = existing_by_email
                except Exception as e:
                    auth_service.db.rollback()
                    logger.error(f"Linking existing user failed: {e}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User sync failed")
            else:
                # Create a brand-new row
                try:
                    user = auth_service.user_service.create(
                        db=auth_service.db,
                        obj_in=UserCreate(
                            email=user_data.user.email,
                            display_name=(user_data.user.user_metadata or {}).get("display_name"),
                            first_name=(user_data.user.user_metadata or {}).get("first_name"),
                            last_name=(user_data.user.user_metadata or {}).get("last_name"),
                            supabase_user_id=uid,
                            is_verified=user_data.user.email_confirmed_at is not None,
                        ),
                    )
                except Exception as e:
                    logger.error(f"Auto-provisioning local user failed: {e}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User sync failed")
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

# Ensures the user has verified their email address before accessing certain features.
async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current verified user"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user

# These are aliases that make your route definitions more readable
def require_auth(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require authentication (alias for get_current_user)"""
    return current_user

def require_verified_user(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Require verified user"""
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Return User if the token is valid, else None (never raises)."""
    if not credentials:
        return None

    # Build a fresh AuthService instance (mirrors get_auth_service) to reuse existing logic
    auth_service = AuthService(db)

    try:
        return await get_current_user(credentials, auth_service)
    except HTTPException:
        return None