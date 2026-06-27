from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.database import get_db
from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_user, get_current_active_user, get_auth_service
from app.core.rate_limit import limiter
from app.schemas.auth import (
    UserRegister, UserLogin, RefreshTokenRequest,
    PasswordResetRequest, ResendVerificationRequest, AuthResponse, PasswordUpdate
)
from app.schemas.user import User as UserSchema
from app.models.user import User
from app.auth.supabase_client import supabase_client

router = APIRouter()

@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
@limiter.limit("3/hour")
async def register(
    request: Request,
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Registers a new user. Rate limit: 3/hour per IP (BE-RL-001)."""
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Authenticates a user and returns a token. Rate limit: 10/minute (BE-RL-001)."""
    result = await auth_service.login_user(login_data)
    return AuthResponse(**result)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logs out the current user."""
    token = authorization.split(" ")[1]
    await auth_service.logout_user(token)
    return

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Refreshes an access token."""
    result = await auth_service.refresh_token(refresh_data.refresh_token)
    return AuthResponse(**result)

@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Sends a password reset email. Rate limit: 3/hour (BE-RL-001)."""
    await auth_service.send_password_reset(reset_data.email)
    return

@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    resend_data: ResendVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Resends an email verification link."""
    await auth_service.resend_verification(resend_data.email)
    return

@router.post("/change-password", response_model=Dict[str, str])
async def change_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Changes the current user's password."""
    await auth_service.change_password(current_user.email, password_data)
    return {"message": "Password changed successfully"}

@router.get("/health")
async def auth_health(auth_service: AuthService = Depends(get_auth_service)):
    """Authentication service health check."""
    return {
        "status": "healthy",
        "service": "authentication",
        "supabase_configured": supabase_client.is_configured()
    }