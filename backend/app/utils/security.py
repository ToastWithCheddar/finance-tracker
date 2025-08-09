from passlib.context import CryptContext
# REMOVED: JWT imports - No longer needed for Supabase-only auth
# from jose import JWTError, jwt
# from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import string

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

# REMOVED: create_access_token() - Using Supabase-only authentication
# Custom JWT tokens no longer needed

# REMOVED: verify_token() - Using Supabase-only authentication
# Custom JWT verification no longer needed

def generate_random_string(length: int = 32) -> str:
    """Generate a random string for tokens"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_reset_token() -> str:
    """Generate a password reset token"""
    return generate_random_string(64)

def generate_verification_token() -> str:
    """Generate an email verification token"""
    return generate_random_string(48)

# REMOVED: create_email_magic_token() - Using Supabase native email confirmation
# Magic tokens no longer needed

# REMOVED: verify_email_magic_token() - Using Supabase native email confirmation
# Magic token verification no longer needed