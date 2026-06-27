from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from contextlib import contextmanager
import uuid
import logging
import secrets
from gotrue.errors import AuthError
from jose import jwt, JWTError
import httpx

# New import for on-the-fly user creation
from app.schemas.user import UserCreate

from app.database import get_db
from app.auth.supabase_client import supabase_client
from app.services.user_service import UserService
from app.models.user import User
from app.auth.auth_service import AuthService
from app.config import settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get the authentication service"""
    return AuthService(db)

def _provision_user_from_supabase(auth_service: AuthService, user_data) -> User:
    """Provisions a local user record from Supabase user data.

    BE-CONC-001: race-safe — uses INSERT ... ON CONFLICT DO NOTHING and re-reads
    the row whether it was inserted or already existed. Concurrent first-login
    requests for the same Supabase user converge to a single row.
    """

    uid = uuid.UUID(user_data.user.id)
    email = user_data.user.email
    is_verified = user_data.user.email_confirmed_at is not None
    metadata = user_data.user.user_metadata or {}
    display_name = metadata.get("display_name")
    first_name = metadata.get("first_name")
    last_name = metadata.get("last_name")

    # Check if a local user exists with the same e-mail (created earlier without UID)
    existing_by_email = auth_service.user_service.get_by_email(
        db=auth_service.db,
        email=email,
    )

    if existing_by_email:
        # Link the Supabase UID to that user and update verification flag.
        # Use a UPDATE-and-fetch path that tolerates concurrent updates.
        try:
            if existing_by_email.supabase_user_id != uid or existing_by_email.is_verified != is_verified:
                existing_by_email.supabase_user_id = uid
                existing_by_email.is_verified = is_verified
                auth_service.db.add(existing_by_email)
                auth_service.db.commit()
                auth_service.db.refresh(existing_by_email)
            return existing_by_email
        except Exception as e:
            auth_service.db.rollback()
            logger.error(f"Linking existing user failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User sync failed")

    # Race-safe insert path. ON CONFLICT on (email) and (supabase_user_id)
    # both DO NOTHING. We then SELECT the row by either key — whichever
    # request "won" the race owns the row, the loser still gets the same row.
    try:
        new_id = uuid.uuid4()
        auth_service.db.execute(
            text(
                """
                INSERT INTO users (
                    id, email, supabase_user_id, display_name,
                    first_name, last_name, is_verified, is_active,
                    locale, timezone, currency, notifications_enabled,
                    theme, auto_categorization_enabled, default_items_per_page,
                    created_at, updated_at
                )
                VALUES (
                    :id, :email, :supabase_user_id, :display_name,
                    :first_name, :last_name, :is_verified, TRUE,
                    'en-US', 'UTC', 'USD', TRUE,
                    'light', TRUE, 25,
                    NOW(), NOW()
                )
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {
                "id": new_id,
                "email": email,
                "supabase_user_id": uid,
                "display_name": display_name,
                "first_name": first_name,
                "last_name": last_name,
                "is_verified": is_verified,
            },
        )
        auth_service.db.commit()
    except Exception as e:
        # Fall back to ORM create path (e.g. SQLite test backends that
        # don't support the ON CONFLICT syntax above).
        auth_service.db.rollback()
        logger.warning(f"Race-safe INSERT failed, falling back to ORM create: {e}")
        try:
            return auth_service.user_service.create(
                db=auth_service.db,
                obj_in=UserCreate(
                    email=email,
                    display_name=display_name,
                    first_name=first_name,
                    last_name=last_name,
                    supabase_user_id=uid,
                    is_verified=is_verified,
                ),
            )
        except Exception:
            # Likely the loser of a race — try a final read.
            auth_service.db.rollback()
            existing = auth_service.user_service.get_by_email(db=auth_service.db, email=email)
            if existing:
                return existing
            logger.error(f"Auto-provisioning local user failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User sync failed")

    # Re-read after the INSERT (or the conflict).
    user = auth_service.user_service.get_by_supabase_id(
        db=auth_service.db, supabase_user_id=uid
    ) or auth_service.user_service.get_by_email(
        db=auth_service.db, email=email
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User sync failed")
    return user

def _validate_dev_token(token: str, auth_service: AuthService) -> Optional[User]:
    """Validates development mock tokens and returns/creates dev user.

    BE-SEC-002: only fires when **all three** flags are true:
      ENVIRONMENT == 'development' AND DEBUG AND ENABLE_ADMIN_BYPASS.
    Defaults are hardened (ENABLE_ADMIN_BYPASS=False) so this code path is
    inert outside of explicit local development.
    """
    from app.config import settings
    bypass_enabled = (
        getattr(settings, "ENVIRONMENT", "production") == "development"
        and bool(getattr(settings, "DEBUG", False))
        and bool(getattr(settings, "ENABLE_ADMIN_BYPASS", False))
    )
    if bypass_enabled:
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
    return None

async def _validate_supabase_token(token: str, auth_service: AuthService):
    """Validates token with Supabase and returns user data.

    BE-SEC-008: the supabase-py client is synchronous and does blocking HTTP
    I/O. Calling it directly from an async route blocks the event loop, so
    we run it in a worker thread.
    """
    import asyncio
    loop = asyncio.get_running_loop()
    user_data = await loop.run_in_executor(
        None, auth_service.supabase.client.auth.get_user, token
    )
    if not user_data or not user_data.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return user_data

def _get_or_provision_local_user(user_data, auth_service: AuthService) -> User:
    """Gets existing local user or provisions new one from Supabase data"""
    # Try to fetch matching local user row
    user = auth_service.user_service.get_by_supabase_id(
        db=auth_service.db,
        supabase_user_id=uuid.UUID(user_data.user.id)
    )

    # Automatically provision a local record if it doesn't exist (first login from older account)
    if not user:
        user = _provision_user_from_supabase(auth_service, user_data)
    
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Gets the current authenticated user from a token"""
    token = credentials.credentials
    
    # Development mode: accept mock tokens
    dev_user = _validate_dev_token(token, auth_service)
    if dev_user:
        return dev_user
    
    try:
        # Single Supabase token validation path
        user_data = await _validate_supabase_token(token, auth_service)
        user = _get_or_provision_local_user(user_data, auth_service)
        return user
        
    except AuthError as e:
        logger.error(f"Supabase authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )
    except (ValueError, KeyError) as e:
        logger.error(f"Token parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format."
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error."
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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """BE-SEC-007: gate admin-only endpoints behind the `is_admin` flag."""
    if not bool(getattr(current_user, "is_admin", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Return User if the token is valid, else None"""
    if not credentials:
        return None

    # Build a fresh AuthService instance to reuse existing logic
    auth_service = AuthService(db)

    try:
        return await get_current_user(credentials, auth_service)
    except HTTPException:
        return None

@contextmanager
def user_context_db(db: Session, user: User):
    """Context manager to set user ID in the database session for RLS"""
    # User will not be able to access the other users information (rows)
    try:
        # Set the user ID for the current transaction 
        db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(user.id)})
        yield db
    finally:
        # The setting is automatically cleared at the end of the transaction
        pass

def get_db_with_user_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FastAPI dependency to provide a DB session with the user context set for RLS.

    BE-SEC-001: this MUST be a generator that yields *inside* the
    `user_context_db` context, otherwise `SET LOCAL` is rolled back before
    the route handler ever runs and Postgres RLS policies see a NULL GUC.
    """
    with user_context_db(db, current_user) as session:
        yield session

def verify_supabase_webhook(authorization: Optional[str] = Header(None)) -> bool:
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
    # Constant-time comparison to avoid leaking the secret via timing (BE-SEC-009).
    secret_matches = secrets.compare_digest(
        secret.encode("utf-8"),
        settings.SUPABASE_WEBHOOK_SECRET.encode("utf-8"),
    )
    if scheme.lower() != "bearer" or not secret_matches:
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
        # Dev mock-token bypass (gated behind three flags — see BE-SEC-002).
        dev_user = _validate_dev_token(token, auth_service)
        if dev_user:
            return dev_user

        # Supabase token validation (run sync client off the event loop).
        import asyncio
        loop = asyncio.get_running_loop()
        user_data = await loop.run_in_executor(
            None, auth_service.supabase.client.auth.get_user, token
        )
        if not user_data or not user_data.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

        # Get or create local user record
        user = auth_service.user_service.get_by_supabase_id(
            db=auth_service.db,
            supabase_user_id=uuid.UUID(user_data.user.id)
        )

        if not user:
            # Auto-provision user if they exist in Supabase but not locally
            user = _provision_user_from_supabase(auth_service, user_data)
        
        return user
        
    except AuthError as e:
        logger.error(f"Supabase authentication failed for token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials from token."
        )
    except (ValueError, KeyError) as e:
        logger.error(f"Token parsing error in get_current_user_from_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format."
        )
    except Exception as e:
        logger.error(f"Unexpected token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error."
        )

async def verify_plaid_webhook(plaid_verification: str = Header(..., alias="Plaid-Verification")):
    """Verifies the JWT sent by Plaid in the webhook verification header."""
    try:
        # 1. Fetch Plaid's public keys (JWKS)
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