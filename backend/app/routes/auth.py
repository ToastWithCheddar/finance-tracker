from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.database import get_db
from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_user, get_current_active_user, get_auth_service
from app.schemas.auth import (
    UserRegister, UserLogin, RefreshTokenRequest,
    PasswordResetRequest, ResendVerificationRequest, AuthResponse, StandardAuthResponse
)
from app.schemas.user import PasswordUpdate
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