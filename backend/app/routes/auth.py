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
    EmailVerification, ResendVerificationRequest, AuthResponse, StandardAuthResponse
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

@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    verification_data: EmailVerification,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Verifies a user's email address."""
    success = await auth_service.verify_email(
        verification_data.token,
        verification_data.email
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token.")
    return AuthResponse(success=True, message="Email verified successfully.")

@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    resend_data: ResendVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Resends an email verification link."""
    await auth_service.resend_verification(resend_data.email)
    return

@router.get("/confirm-email", response_class=RedirectResponse)
async def confirm_email(
    token: str = Query(...),
    redirect: str = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service)
) -> RedirectResponse:
    """
    Magic link email confirmation endpoint.
    Verifies the token, marks email as verified, creates session tokens,
    and redirects to the frontend with cookies set.
    """
    try:
        # Verify magic token and create session
        auth_data = await auth_service.verify_magic_link_and_login(token)
        
        # Default redirect to dashboard if not specified
        from app.config import settings
        redirect_url = redirect or f"{settings.FRONTEND_URL}/dashboard"
        
        # Create redirect response
        response = RedirectResponse(url=redirect_url, status_code=302)
        
        # Set HttpOnly cookies for tokens
        if auth_data.get("accessToken"):
            response.set_cookie(
                "access_token",
                auth_data["accessToken"],
                httponly=True,
                secure=True,  # Only over HTTPS in production
                samesite="lax",
                max_age=15 * 60,  # 15 minutes
                path="/"
            )
        
        if auth_data.get("refreshToken"):
            response.set_cookie(
                "refresh_token",
                auth_data["refreshToken"],
                httponly=True,
                secure=True,  # Only over HTTPS in production
                samesite="lax",
                max_age=7 * 24 * 60 * 60,  # 7 days
                path="/"
            )
            
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 404, etc.)
        raise
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Magic link confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email confirmation failed"
        )

@router.get("/health")
async def auth_health(auth_service: AuthService = Depends(get_auth_service)):
    """Authentication service health check."""
    return {
        "status": "healthy",
        "service": "authentication",
        "supabase_configured": supabase_client.is_configured()
    }