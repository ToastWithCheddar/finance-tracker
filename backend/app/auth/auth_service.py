from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from gotrue.errors import AuthError
import logging
from datetime import datetime, timedelta, timezone
import uuid
from jose import jwt

from app.auth.supabase_client import supabase_client
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, PasswordResetRequest, PasswordUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService
from app.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

class AuthService:
    ALGORITHM = "HS256"
    
    def __init__(self, db: Session):
        self.db = db
        self.supabase = supabase_client
        if not self.supabase.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not configured."
            )
        self.user_service = UserService()
        # Use Supabase JWT secret if available, fallback to app JWT secret for development
        self.supabase_jwt_secret = settings.SUPABASE_JWT_SECRET

        # ADD THIS LINE FOR DEBUGGING
        print(f"--- Loaded SUPABASE_JWT_SECRET: '{self.supabase_jwt_secret}' ---")
        if not self.supabase_jwt_secret:
            logger.warning("No JWT secret configured - denylist functionality may not work in production")

    async def _create_local_user(self, user_data: UserRegister, supabase_user_id: uuid.UUID) -> User:
        """Creates a user in the local database."""
        user_create = UserCreate(
            email=user_data.email,
            display_name=user_data.display_name,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            supabase_user_id=supabase_user_id,
        )
        return self.user_service.create(db=self.db, obj_in=user_create)

    async def register_user(self, user_data: UserRegister) -> Dict[str, Any]:
        """Registers a new user with Supabase and the local database."""
        if self.user_service.get_by_email(db=self.db, email=user_data.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

        try:
            auth_response = self.supabase.client.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "display_name": user_data.display_name,
                        "first_name": user_data.first_name,
                        "last_name": user_data.last_name,
                    }
                }
            })
            if not auth_response.user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create user.")

            db_user = await self._create_local_user(user_data, uuid.UUID(auth_response.user.id))
            
            # Supabase automatically sends email confirmation
            # No custom magic link needed
            
            user_dict = {
                "id": str(db_user.id),
                "email": db_user.email,
                "displayName": db_user.display_name,
                "avatarUrl": db_user.avatar_url,
                "locale": db_user.locale,
                "timezone": db_user.timezone,
                "currency": db_user.currency,
                "createdAt": db_user.created_at.isoformat() if db_user.created_at else None,
                "updatedAt": db_user.updated_at.isoformat() if db_user.updated_at else None,
                "isActive": db_user.is_active,
                "emailSent": True,  # Indicate that email confirmation was sent
            }
            return {
                "user": user_dict,
                "message": "Registration successful! Please check your email to confirm your account.",
                "requiresEmailConfirmation": True,
                # No tokens returned - user must confirm email via Supabase first
            }
        except AuthError as e:
            logger.error(f"Supabase registration error: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")
    
    async def login_user(self, login_data: UserLogin) -> Dict[str, Any]:
        """Authenticates a user with Supabase."""
        try:
            auth_response = self.supabase.client.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            if not auth_response.user or not auth_response.session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
            
            db_user = self.user_service.get_by_email(db=self.db, email=login_data.email)
            if not db_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
            # Check if the user account is active
            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Account has been deactivated."
                )

            user_dict = {
                "id": str(db_user.id),
                "email": db_user.email,
                "displayName": db_user.display_name,
                "avatarUrl": db_user.avatar_url,
                "locale": db_user.locale,
                "timezone": db_user.timezone,
                "currency": db_user.currency,
                "createdAt": db_user.created_at.isoformat() if db_user.created_at else None,
                "updatedAt": db_user.updated_at.isoformat() if db_user.updated_at else None,
                "isActive": db_user.is_active,
            }
            return {
                "user": user_dict,
                "accessToken": auth_response.session.access_token if auth_response.session else None,
                "refreshToken": auth_response.session.refresh_token if auth_response.session else None,
                "expiresIn": 15 * 60
            }
        except AuthError as e:
            logger.error(f"Supabase login error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes a user's access token using Supabase only."""
        try:
            # Use Supabase refresh session directly
            auth_response = self.supabase.client.auth.refresh_session(refresh_token)
            if not auth_response.session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

            # Get user data for Supabase refresh
            user_data = self.supabase.client.auth.get_user(auth_response.session.access_token)
            if not user_data or not user_data.user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session after refresh.")
            
            db_user = self.user_service.get_by_email(db=self.db, email=user_data.user.email)
            if not db_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
            # Check if the user account is active
            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Account has been deactivated."
                )

            user_dict = {
                "id": str(db_user.id),
                "email": db_user.email,
                "displayName": db_user.display_name,
                "first_name": db_user.first_name,
                "last_name": db_user.last_name,
                "avatar_url": db_user.avatar_url,
                "locale": db_user.locale,
                "timezone": db_user.timezone,
                "currency": db_user.currency,
                "is_active": db_user.is_active,
                "is_verified": db_user.is_verified,
                "notification_email": db_user.notification_email,
                "notification_push": db_user.notification_push,
                "theme": db_user.theme,
                "createdAt": db_user.created_at.isoformat() if db_user.created_at else None,
                "updatedAt": db_user.updated_at.isoformat() if db_user.updated_at else None,
            }

            return {
                "user": user_dict,
                "accessToken": auth_response.session.access_token,
                "refreshToken": auth_response.session.refresh_token,
                "expiresIn": 15 * 60
            }
        except AuthError as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token.")
        except Exception as e:
            logger.error(f"Unexpected token refresh error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed")
    
    async def logout_user(self, access_token: str) -> None:
        """Logs out a user from Supabase and adds the token to the denylist."""
        try:
            # First, sign out from Supabase to invalidate the session server-side
            self.supabase.client.auth.set_session(access_token, "")
            # Note: Supabase's sign_out is not an async function in the version we're likely using
            self.supabase.client.auth.sign_out()

            # Now, add the token to the denylist to invalidate it immediately
            try:
                # We don't need to verify the signature, just decode to get claims
                payload = jwt.decode(
                    access_token, 
                    self.supabase_jwt_secret, 
                    algorithms=[self.ALGORITHM], 
                    options={"verify_signature": False}
                )
                jti = payload.get("jti")  # JWT ID
                exp = payload.get("exp")  # Expiration time

                if jti and exp:
                    # Calculate remaining time to live for the token
                    ttl = exp - int(datetime.now(timezone.utc).timestamp())
                    if ttl > 0:
                        denylist_key = f"denylist:{jti}"
                        await redis_client.set_cache(denylist_key, "logged_out", expire_seconds=ttl)
                        logger.info(f"Token {jti} added to denylist for {ttl} seconds.")
                else:
                    logger.warning("Token missing jti or exp claims - cannot add to denylist")

            except Exception as e:
                logger.error(f"Failed to add token to denylist during logout: {e}")

            logger.info("User logged out successfully")
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            # Do not re-raise; client should still clear local tokens
    
    async def send_password_reset(self, email: str) -> None:
        """Sends a password reset email."""
        try:
            self.supabase.client.auth.reset_password_email(email, {
                "redirect_to": f"{settings.FRONTEND_URL}/reset-password"
            })
        except Exception as e:
            logger.error(f"Password reset email failed: {e}")
            # Do not re-raise, to avoid leaking user existence
    
    async def verify_email(self, token: str, email: str) -> bool:
        """Verifies an email with a token."""
        try:
            response = self.supabase.client.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "email"
            })
            return response.user is not None
        except Exception as e:
            logger.error(f"Email verification failed: {e}")
            return False
    
    async def resend_verification(self, email: str) -> None:
        """Resends email verification."""
        try:
            self.supabase.client.auth.resend({
                "type": "signup",
                "email": email,
                "options": {
                    "redirect_to": f"{settings.FRONTEND_URL}/verify-email"
                }
            })
        except Exception as e:
            logger.error(f"Resend verification failed: {e}")
            # Do not re-raise, to avoid leaking user existence

    async def change_password(self, email: str, password_data: PasswordUpdate) -> None:
        """Changes the user's password via Supabase."""
        try:
            # First, verify the current password by attempting to sign in
            try:
                auth_response = self.supabase.client.auth.sign_in_with_password({
                    "email": email,
                    "password": password_data.current_password
                })
                if not auth_response.user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current password is incorrect"
                    )
            except AuthError as e:
                logger.error(f"Current password verification failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # If current password is correct, update to new password
            # Note: This requires the user to be signed in, so we need to get their session
            update_response = self.supabase.client.auth.update_user({
                "password": password_data.new_password
            })
            
            if not update_response.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update password"
                )
                
            logger.info(f"Password changed successfully for user: {email}")
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Password change failed for {email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )

    # REMOVED: create_magic_link_token() - No longer needed for Supabase-only auth

    # REMOVED: verify_magic_link_and_login() - Using Supabase native email confirmation

    # REMOVED: _send_magic_link_email() - Using Supabase native email confirmation