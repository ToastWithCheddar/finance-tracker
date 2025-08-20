from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Dict, Any
import re  
from uuid import UUID


def validate_strong_password(password: str) -> str:
    """Centralized password validation function."""
    if not re.search(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", password):
        raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')
    return password  

class UserRegister(BaseModel):  
    email: EmailStr  
    password: str = Field(..., min_length=8, max_length=100)  
    display_name: str | None = Field(None, min_length=1, max_length=100)  
    first_name: str | None = Field(None, min_length=1, max_length=50)  
    last_name: str | None = Field(None, min_length=1, max_length=50)  
    
    @field_validator('password')  
    @classmethod  
    def validate_password(cls, v: str) -> str:  
        return validate_strong_password(v)  

class UserLogin(BaseModel):  
    email: EmailStr  
    password: str = Field(..., min_length=1)  
    remember_me: bool = False  

class TokenResponse(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    expires_in: int | None = None  
    expires_at: int | None = None  
    refresh_token: str | None = None
    user_id: UUID | None = None  

class RefreshTokenRequest(BaseModel):  
    refresh_token: str  

class PasswordResetRequest(BaseModel):  
    email: EmailStr  

class PasswordResetConfirm(BaseModel):  
    token: str  
    new_password: str = Field(..., min_length=8, max_length=100)  
    
    @field_validator('new_password')  
    @classmethod  
    def validate_new_password(cls, v: str) -> str:  
        return validate_strong_password(v)  

class PasswordUpdate(BaseModel):  
    current_password: str  
    new_password: str = Field(..., min_length=8, max_length=100)  
    
    @field_validator('new_password')  
    @classmethod  
    def validate_new_password(cls, v: str) -> str:  
        return validate_strong_password(v)
    
    @model_validator(mode="after")
    def check_passwords_are_different(self):
        if self.current_password == self.new_password:
            raise ValueError('New password must be different from current password')
        return self  

class EmailVerification(BaseModel):  
    token: str  
    email: EmailStr  

class ResendVerificationRequest(BaseModel):  
    email: EmailStr  

class AuthResponse(BaseModel):  
    user: Dict[str, Any]
    tokens: TokenResponse
