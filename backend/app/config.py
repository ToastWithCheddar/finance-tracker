from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:devpassword123@localhost:5432/postgres")
    
    # Security Configuration - Must be set via environment variables
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Supabase Configuration - Must be set via environment variables
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # Application Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "debug")
    
    # Frontend Configuration
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
    ]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # Machine Learning Service
    ML_SERVICE_URL: str = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
    ML_CONFIDENCE_THRESHOLD: float = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.6"))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Security Settings
    ENABLE_ADMIN_BYPASS: bool = os.getenv("ENABLE_ADMIN_BYPASS", "true").lower() in ("true", "1", "yes")
    CSRF_PROTECTION: bool = os.getenv("CSRF_PROTECTION", "false").lower() in ("true", "1", "yes")
    RATE_LIMITING: bool = os.getenv("RATE_LIMITING", "false").lower() in ("true", "1", "yes")
    
    # Feature Toggles
    ENABLE_DATABASE: bool = os.getenv("ENABLE_DATABASE", "true").lower() in ("true", "1", "yes")
    ENABLE_REDIS: bool = os.getenv("ENABLE_REDIS", "true").lower() in ("true", "1", "yes")
    ENABLE_ML_WORKER: bool = os.getenv("ENABLE_ML_WORKER", "true").lower() in ("true", "1", "yes")
    ENABLE_PLAID: bool = os.getenv("ENABLE_PLAID", "true").lower() in ("true", "1", "yes")
    ENABLE_EMAIL: bool = os.getenv("ENABLE_EMAIL", "false").lower() in ("true", "1", "yes")
    
    # Plaid Configuration
    PLAID_CLIENT_ID: str = os.getenv("PLAID_CLIENT_ID", "")
    PLAID_SECRET: str = os.getenv("PLAID_SECRET", "")
    PLAID_ENV: str = os.getenv("PLAID_ENV", "sandbox")
    PLAID_PRODUCTS: str = os.getenv("PLAID_PRODUCTS", "transactions,accounts")
    PLAID_COUNTRY_CODES: str = os.getenv("PLAID_COUNTRY_CODES", "US")
    
    # Mock/Demo Mode
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "false").lower() in ("true", "1", "yes")
    UI_ONLY_MODE: bool = os.getenv("UI_ONLY_MODE", "false").lower() in ("true", "1", "yes")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_required_settings()
    
    def validate_required_settings(self):
        """Validate that all required settings are provided"""
        if self.is_production:
            required_fields = ["SECRET_KEY", "JWT_SECRET_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
            missing_fields = []
            
            for field in required_fields:
                value = getattr(self, field, None)
                if not value or (isinstance(value, str) and (value.startswith("your-") or len(value.strip()) == 0)):
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required environment variables for production: {', '.join(missing_fields)}")
        
        # For development, warn if critical secrets are missing but don't fail
        if self.is_development:
            critical_fields = ["SECRET_KEY", "JWT_SECRET_KEY"]
            missing_fields = []
            
            for field in critical_fields:
                value = getattr(self, field, None)
                if not value or len(value.strip()) == 0:
                    missing_fields.append(field)
            
            if missing_fields:
                import warnings
                warnings.warn(f"Missing development environment variables (will use generated defaults): {', '.join(missing_fields)}")
                
                # Generate temporary secrets for development
                import secrets
                if not self.SECRET_KEY:
                    self.SECRET_KEY = secrets.token_urlsafe(32)
                if not self.JWT_SECRET_KEY:
                    self.JWT_SECRET_KEY = secrets.token_urlsafe(32)
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["production", "prod"]

# Create settings instance
settings = Settings()