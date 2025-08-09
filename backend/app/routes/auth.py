from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.database import get_db
from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_user, get_current_active_user, get_auth_service
from app.schemas.auth import (
    UserRegister, UserLogin, RefreshTokenRequest,
    PasswordResetRequest, PasswordUpdate,
    ResendVerificationRequest, AuthResponse, StandardAuthResponse
    # REMOVED: EmailVerification - No longer needed for Supabase-only auth
)
from app.schemas.user import User as UserSchema
from app.models.user import User
from app.auth.supabase_client import supabase_client

router = APIRouter()

@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def register(
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Registers a new user."""
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=StandardAuthResponse)
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> StandardAuthResponse:
    """Authenticates a user and returns a token."""
    result = await auth_service.login_user(login_data)
    return StandardAuthResponse(**result)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logs out the current user."""
    token = authorization.split(" ")[1]
    await auth_service.logout_user(token)
    return

@router.post("/refresh", response_model=StandardAuthResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> StandardAuthResponse:
    """Refreshes an access token."""
    result = await auth_service.refresh_token(refresh_data.refresh_token)
    return StandardAuthResponse(**result)

@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Sends a password reset email."""
    await auth_service.send_password_reset(reset_data.email)
    return

# REMOVED: /verify-email endpoint - Using Supabase native email verification
# Email verification is handled automatically by Supabase through their confirmation emails

@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    resend_data: ResendVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Resends an email verification link."""
    await auth_service.resend_verification(resend_data.email)
    return

# REMOVED: /confirm-email endpoint - Using Supabase native email confirmation
# Supabase handles email confirmation automatically through their dashboard configuration

@router.get("/health")
async def auth_health(auth_service: AuthService = Depends(get_auth_service)):
    """Authentication service health check."""
    return {
        "status": "healthy",
        "service": "authentication",
        "supabase_configured": supabase_client.is_configured()
    }