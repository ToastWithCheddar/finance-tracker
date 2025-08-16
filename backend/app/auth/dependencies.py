from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from contextlib import contextmanager
import uuid
import logging
from gotrue.errors import AuthError
from jose import jwt, JWTError, jwk
import httpx

# New import for on-the-fly user creation
from app.schemas.user import UserCreate

from app.database import get_db
from app.auth.supabase_client import supabase_client
from app.services.user_service import UserService
from app.models.user import User
from app.auth.auth_service import AuthService
from app.core.redis_client import redis_client
from app.config import settings

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
        # Single Supabase token validation path
        user_data = auth_service.supabase.client.auth.get_user(token)
        if not user_data or not user_data.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        
        # # Check if the token has been denylisted (logged out)
        # try:
        #     supabase_jwt_secret = settings.SUPABASE_JWT_SECRET or settings.JWT_SECRET_KEY
        #     if supabase_jwt_secret:
        #         payload = jwt.decode(
        #             token, 
        #             supabase_jwt_secret, 
        #             algorithms=["HS256"], 
        #             options={"verify_signature": False}
        #         )
        #         jti = payload.get("jti")
        #         if jti:
        #             is_denylisted = await redis_client.key_exists(f"denylist:{jti}")
        #             if is_denylisted:
        #                 logger.warning(f"Attempt to use a denylisted token for user: {user_data.user.email}")
        #                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been invalidated.")
        # except JWTError:
        #     # If decoding fails here (it shouldn't if Supabase passed it), deny access
        #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")
        # except Exception as e:
        #     logger.error(f"Error checking token denylist: {e}")
        #     # Continue without denylist check in case Redis is down - log the issue
        
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
        
    except AuthError as e:
        logger.error(f"Supabase authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed."
        )

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

@contextmanager
def user_context_db(db: Session, user: User):
    """Context manager to set user ID in the database session for Row-Level Security."""
    try:
        # Set the user ID for the current transaction (reusing audit pattern)
        db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(user.id)})
        yield db
    finally:
        # The setting is automatically cleared at the end of the transaction
        # No explicit reset is needed with SET LOCAL
        pass

def get_db_with_user_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Session:
    """FastAPI dependency to provide a DB session with the user context set for RLS."""
    with user_context_db(db, current_user) as session:
        return session

def verify_supabase_webhook(
    authorization: Optional[str] = Header(None)
) -> bool:
    """Verifies the Authorization header from a Supabase webhook."""
    if not settings.SUPABASE_WEBHOOK_SECRET:
        logger.error("SUPABASE_WEBHOOK_SECRET is not set. Cannot verify webhook.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured.",
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header.",
        )

    scheme, _, secret = authorization.partition(" ")
    if scheme.lower() != "bearer" or secret != settings.SUPABASE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret.",
        )
    return True


async def get_current_user_from_token(
    token: str, 
    db: Session = Depends(get_db)
) -> User:
    """Gets the current authenticated user from a token string."""
    auth_service = AuthService(db)
    
    try:
        # Supabase token validation
        user_data = auth_service.supabase.client.auth.get_user(token)
        if not user_data or not user_data.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

        # Check denylist (for logged-out tokens)
        # Note: Supabase already validated the token; we only need unverified claims to read JTI.
        try:
            supabase_jwt_secret = settings.SUPABASE_JWT_SECRET or settings.JWT_SECRET_KEY
            if supabase_jwt_secret:
                # Avoid validating claims like aud/exp when we're only reading JTI
                payload = jwt.get_unverified_claims(token)
                jti = payload.get("jti")
                if jti and await redis_client.key_exists(f"denylist:{jti}"):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been invalidated.")
        except JWTError:
            # If claims cannot be read, skip denylist check but do not block auth
            logger.warning("Failed to read unverified JWT claims for denylist check; proceeding without denylist validation")

        # Get or create local user record
        user = auth_service.user_service.get_by_supabase_id(
            db=auth_service.db,
            supabase_user_id=uuid.UUID(user_data.user.id)
        )

        if not user:
            # Auto-provision user if they exist in Supabase but not locally
            user = auth_service.user_service.create(
                db=auth_service.db,
                obj_in=UserCreate(
                    email=user_data.user.email,
                    supabase_user_id=uuid.UUID(user_data.user.id),
                    is_verified=user_data.user.email_confirmed_at is not None,
                ),
            )
        
        return user
        
    except AuthError as e:
        logger.error(f"Supabase authentication failed for token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials from token."
        )
    except Exception as e:
        logger.error(f"Token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed."
        )

async def verify_plaid_webhook(
    plaid_verification: str = Header(..., alias="Plaid-Verification")
):
    """Verifies the JWT sent by Plaid in the webhook verification header."""
    try:
        # 1. Fetch Plaid's public keys (JWKS)
        # In production, these should be cached for a few hours.
        async with httpx.AsyncClient() as client:
            jwks_response = await client.post(
                f"{settings.PLAID_BASE_URL}/webhook_verification_key/get", 
                json={
                    "client_id": settings.PLAID_CLIENT_ID, 
                    "secret": settings.PLAID_SECRET
                }
            )
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

        # 2. Decode the header to find the Key ID ('kid')
        unverified_header = jwt.get_unverified_header(plaid_verification)
        kid = unverified_header.get("kid")
        
        # 3. Find the matching public key
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Webhook public key not found.")

        # 4. Verify the token's signature and claims
        jwt.decode(
            plaid_verification,
            key,
            algorithms=[key["alg"]],
            options={"verify_aud": False}  # Audience is not standard
        )
        return True

    except JWTError as e:
        logger.error(f"Plaid webhook JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")
    except Exception as e:
        logger.error(f"Plaid webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Webhook verification failed.")