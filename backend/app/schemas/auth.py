from pydantic import BaseModel, EmailStr, Field, field_validator  
from typing import Optional  
import re  
from uuid import UUID  

class UserRegister(BaseModel):  
    email: EmailStr  
    password: str = Field(..., min_length=8, max_length=100)  
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)  
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)  
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)  
    
    @field_validator('password')  
    @classmethod  
    def validate_password(cls, v: str) -> str:  
        if not re.search(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):  
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')  
        return v  

class UserLogin(BaseModel):  
    email: EmailStr  
    password: str = Field(..., min_length=1)  
    remember_me: bool = False  

class TokenResponse(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user_id: UUID  
    expires_in: Optional[int] = None  
    expires_at: Optional[int] = None  
    refresh_token: Optional[str] = None  

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
        if not re.search(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):  
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')  
        return v  

class PasswordUpdate(BaseModel):  
    current_password: str  
    new_password: str = Field(..., min_length=8, max_length=100)  
    
    @field_validator('new_password')  
    @classmethod  
    def validate_new_password(cls, v: str) -> str:  
        if not re.search(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)", v):  
            raise ValueError('Password must contain at least one lowercase letter, one uppercase letter, and one digit')  
        return v  

class EmailVerification(BaseModel):  
    token: str  
    email: EmailStr  

class ResendVerificationRequest(BaseModel):  
    email: EmailStr  

class StandardAuthResponse(BaseModel):
    user: dict
    accessToken: str
    refreshToken: str
    expiresIn: Optional[int] = None
    tokenType: str = "bearer"

# Keep original for backward compatibility
class AuthResponse(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user_id: UUID  
    expires_in: Optional[int] = None  
    expires_at: Optional[int] = None  
    refresh_token: Optional[str] = None
