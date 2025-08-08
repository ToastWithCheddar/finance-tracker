from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from gotrue.errors import AuthError
import logging
from datetime import datetime, timedelta
import uuid

from app.auth.supabase_client import supabase_client
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, PasswordResetRequest, PasswordUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService
from app.config import settings
from app.utils.security import create_email_magic_token, verify_email_magic_token, create_access_token

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.supabase = supabase_client
        if not self.supabase.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not configured."
            )
        self.user_service = UserService()

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
            
            # Send magic link for email confirmation instead of immediate login
            magic_token = self.create_magic_link_token(str(db_user.id))
            
            # Send email with magic link
            await self._send_magic_link_email(
                db_user.email, 
                magic_token, 
                db_user.display_name or db_user.first_name or "User"
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
                "emailSent": True,  # Indicate that email confirmation was sent
            }
            return {
                "user": user_dict,
                "message": "Registration successful! Please check your email for a confirmation link.",
                "requiresEmailConfirmation": True,
                # Don't return tokens immediately - user must confirm email first
            }
        except AuthError as e:
            logger.error(f"Supabase registration error: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
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
                "expiresIn": 15 * 60,
                "tokenType": "supabase"
            }
        except AuthError as e:
            logger.error(f"Supabase login error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes a user's access token."""
        try:
            # First, try to verify as our custom JWT refresh token
            from app.utils.security import verify_token
            custom_payload = verify_token(refresh_token)
            if custom_payload and custom_payload.get('type') == 'refresh' and custom_payload.get('user_id'):
                # This is our custom refresh token - create new tokens
                user_id = custom_payload['user_id']
                db_user = self.user_service.get(db=self.db, id=user_id)
                if not db_user or not db_user.is_active:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
                
                # Create new access and refresh tokens
                access_token_data = {
                    "sub": str(db_user.id),
                    "email": db_user.email,
                    "user_id": str(db_user.id)
                }
                new_access_token = create_access_token(access_token_data)
                
                refresh_token_data = {
                    "sub": str(db_user.id),
                    "type": "refresh",
                    "user_id": str(db_user.id)
                }
                new_refresh_token = create_access_token(
                    refresh_token_data, 
                    expires_delta=timedelta(days=7)
                )
                
                # BUILD COMPLETE USER OBJECT
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
                    "accessToken": new_access_token,
                    "refreshToken": new_refresh_token,
                    "expiresIn": 15 * 60,
                    "tokenType": "custom_jwt"
                }
            
            # If not a custom token, try Supabase refresh
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
                "expiresIn": 15 * 60,
                "tokenType": "supabase"
            }
        except AuthError as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token.")
    
    # TODO: Logout doesn't invalidate the token, it just logs the user out of the current session, fix it
    async def logout_user(self, access_token: str) -> None:
        """Logs out a user from Supabase and invalidates the session."""
        try:
            # Set the session first so Supabase knows which session to invalidate
            self.supabase.client.auth.set_session(access_token, "")
            # Sign out to invalidate the session server-side
            await self.supabase.client.auth.sign_out()
            logger.info("User logged out successfully")
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            # Don't re-raise as the client should still clear local tokens

    # The Risk: If a user logs out and their accessToken is stolen before it expires, 
    # an attacker could still use it to access the API.
    # The Solution (Token Denylist): For high-security applications, you can implement a "denylist." 
    # When a user logs out, you store the ID of the logged-out token in a fast db with its expiration time
    
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

    def create_magic_link_token(self, user_id: str) -> str:
        """Create a magic link token for email confirmation and automatic login"""
        return create_email_magic_token(user_id)

    async def verify_magic_link_and_login(self, token: str) -> Dict[str, Any]:
        """Verify magic link token and log the user in"""
        payload = verify_email_magic_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid or expired token"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token format"
            )

        # Get user from database
        db_user = self.user_service.get(db=self.db, id=user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Mark email as verified if not already
        if not db_user.is_verified:
            user_update = UserUpdate(is_verified=True)
            db_user = self.user_service.update(db=self.db, db_obj=db_user, obj_in=user_update)

        # Create new JWT tokens for the session (bypassing Supabase for magic link flow)
        try:
            # Create access token with user data
            access_token_data = {
                "sub": str(db_user.id),
                "email": db_user.email,
                "user_id": str(db_user.id)
            }
            access_token = create_access_token(access_token_data)
            
            # Create a longer-lived refresh token
            refresh_token_data = {
                "sub": str(db_user.id),
                "type": "refresh",
                "user_id": str(db_user.id)
            }
            refresh_token = create_access_token(
                refresh_token_data, 
                expires_delta=timedelta(days=7)
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
                "emailVerified": db_user.is_verified,
            }

            return {
                "user": user_dict,
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresIn": 15 * 60,
                "tokenType": "custom_jwt"
            }

        except Exception as e:
            logger.error(f"Magic link verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify magic link"
            )

    async def _send_magic_link_email(self, email: str, magic_token: str, user_name: str) -> None:
        """Send magic link email for account confirmation"""
        try:
            magic_link = f"{settings.API_URL}/auth/confirm-email?token={magic_token}&redirect={settings.FRONTEND_URL}/dashboard"
            
            # For now, just log the magic link (in production, use SendGrid or similar)
            logger.info(f"Magic link for {email}: {magic_link}")
            
            # TODO: Implement actual email sending with template
            # Example structure:
            # email_service.send_template_email(
            #     to=email,
            #     template_id="welcome_magic_link",
            #     template_data={
            #         "user_name": user_name,
            #         "magic_link": magic_link,
            #         "app_name": "Finance Tracker"
            #     }
            # )
            
        except Exception as e:
            logger.error(f"Failed to send magic link email to {email}: {e}")
            # Don't raise exception - we don't want registration to fail if email fails