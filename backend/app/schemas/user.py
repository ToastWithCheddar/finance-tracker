from pydantic import BaseModel, EmailStr, ConfigDict, Field
# No imports needed from typing for this file after modernization
from datetime import datetime 
from uuid import UUID
from .base import BaseResponseSchema


# Base pydantic schema 
class User(BaseResponseSchema):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None

    locale: str = "en-US"
    timezone: str = "UTC"
    currency: str = "USD"

    is_active: bool = True
    is_verified: bool = True

    notification_push: bool = True
    theme: str = "light" 

    # Pydantic v2: allow constructing from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)

### Check below later -----
# *Used by routes* that return the current user's private data
# Complete user data (includes email, settings) - *used when user requests their own profile*
class UserResponse(User):
    """Full user payload for the authenticated user (private)."""
    pass

# Public profile (no email or internal flags)
# Public-safe data only - used when showing user info to other users (no email, no system flags)
class UserProfile(BaseModel):
    id: UUID
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
### 

# Workflow
# 1) Validate the incoming JSON with UserRegister from auth.py (checks email+password strength)
# 2) Send the password off to Supabase (or hash & store it if you were doing that locally)
# 3) Map to a UserCreate (just profile fields + supabase_user_id) and do user_service.create(...)

# Local database create schema (no password required)
class UserCreate(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None

    locale: str | None = "en-US"
    timezone: str | None = "UTC"
    currency: str | None = "USD"

    is_active: bool | None = True
    is_verified: bool | None = False

    notification_push: bool | None = True
    theme: str | None = "light"


# Partial update schema (only contains fields users can modify)
class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    locale: str | None = Field(None, min_length=2, max_length=10)
    timezone: str | None = Field(None, min_length=1, max_length=50)
    currency: str | None = Field(None, min_length=3, max_length=3)
    avatar_url: str | None = None

# All authentication schemas have been moved to auth.py for consistency