from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator
from typing import Optional, Dict, Any
import re
from datetime import datetime 
from uuid import UUID


# Base pydantic schema 
class User(BaseModel):
    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    locale: str = "en-US"
    timezone: str = "UTC"
    currency: str = "USD"

    is_active: bool = True
    is_verified: bool = True

    notification_email: bool = True
    notification_push: bool = True
    theme: str = "light" 

    created_at: datetime
    updated_at: Optional[datetime] = None

    # Pydantic v2: allow constructing from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)

### Check below later -----
# *Used by routes* that return the current user's private data
# Complete user data (includes email, settings) - *used when user requests their own profile*
class UserResponse(User):
    """Full user payload for the authenticated user (private)."""
    pass

# Public profile (no email or internal flags)
# Public-safe data only - used when showing user info to other users (no email, no system flags)
class UserProfile(BaseModel):
    id: UUID
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
### 


# Signup schema (with password validation)
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):
            # Password complexity requirements (uppercase, lowercase, digit)
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')
        return v

# Workflow
# 1) Validate the incoming JSON with UserRegister (checks email+password strength)
# 2) Send the password off to Supabase (or hash & store it if you were doing that locally)
# 3) Map to a UserCreate (just profile fields + supabase_user_id) and do user_service.create(...)

# Local database create schema (no password required)
class UserCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    locale: Optional[str] = "en-US"
    timezone: Optional[str] = "UTC"
    currency: Optional[str] = "USD"

    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False

    notification_email: Optional[bool] = True
    notification_push: Optional[bool] = True
    theme: Optional[str] = "light"


# Partial update schema (only contains fields users can modify)
class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    locale: Optional[str] = Field(None, min_length=2, max_length=10)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    avatar_url: Optional[str] = None


# Auth & token schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1) # minimal checking
    remember_me: bool = False  # to remember for later login

# Standardized token response following OAuth2 conventions
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int
    refresh_token: Optional[str] = None
    # User data to avoid additional API calls
    user: Dict[str, Any]  

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# "Forgot password" - just needs email
class PasswordResetRequest(BaseModel):
    email: EmailStr

# Uses email token to set new password
class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not re.search(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')
        return v

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not re.search(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')
        return v

    @model_validator(mode="after")
    def check_passwords_are_different(self):
        if self.current_password == self.new_password:
            raise ValueError('New  password must be different from current password')
        return self

class EmailVerification(BaseModel):
    token: str
    email: EmailStr

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class AuthResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    