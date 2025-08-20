from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, TYPE_CHECKING
import os
from pathlib import Path

if TYPE_CHECKING:
    from app.schemas.financial_health_config import FinancialHealthConfig

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

    # Supabase Configuration - Must be set via environment variables
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_WEBHOOK_SECRET: str = os.getenv("SUPABASE_WEBHOOK_SECRET", "")

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
    
    # Cache Configuration
    CACHE_DEFAULT_TTL: int = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 minutes
    CACHE_DEFAULT_MAX_SIZE: int = int(os.getenv("CACHE_DEFAULT_MAX_SIZE", "1000"))
    SYNC_JOBS_CACHE_MAX_SIZE: int = int(os.getenv("SYNC_JOBS_CACHE_MAX_SIZE", "500"))
    SYNC_JOBS_CACHE_TTL: int = int(os.getenv("SYNC_JOBS_CACHE_TTL", "900"))  # 15 minutes
    MERCHANT_CACHE_MAX_SIZE: int = int(os.getenv("MERCHANT_CACHE_MAX_SIZE", "2000"))
    MERCHANT_CACHE_TTL: int = int(os.getenv("MERCHANT_CACHE_TTL", "3600"))  # 1 hour
    RULE_CACHE_MAX_SIZE: int = int(os.getenv("RULE_CACHE_MAX_SIZE", "1000"))
    RULE_CACHE_TTL: int = int(os.getenv("RULE_CACHE_TTL", "300"))  # 5 minutes
    
    # Application Scaling
    UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", "1"))
    
    # Financial Health Configuration
    # Balance thresholds (in cents)
    FINANCIAL_HEALTH_BALANCE_NEGATIVE_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_BALANCE_NEGATIVE_PENALTY", "30"))
    FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_THRESHOLD: int = int(os.getenv("FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_THRESHOLD", "10000"))
    FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_BALANCE_LOW_BALANCE_PENALTY", "20"))
    FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_THRESHOLD: int = int(os.getenv("FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_THRESHOLD", "100000"))
    FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_BONUS: int = int(os.getenv("FINANCIAL_HEALTH_BALANCE_GOOD_BALANCE_BONUS", "10"))
    
    # Activity thresholds
    FINANCIAL_HEALTH_ACTIVITY_INACTIVE_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_ACTIVITY_INACTIVE_PENALTY", "20"))
    FINANCIAL_HEALTH_ACTIVITY_HIGH_ACTIVITY_BONUS: int = int(os.getenv("FINANCIAL_HEALTH_ACTIVITY_HIGH_ACTIVITY_BONUS", "10"))
    FINANCIAL_HEALTH_ACTIVITY_SYNC_HOURS_THRESHOLD: int = int(os.getenv("FINANCIAL_HEALTH_ACTIVITY_SYNC_HOURS_THRESHOLD", "24"))
    FINANCIAL_HEALTH_ACTIVITY_SYNC_BONUS: int = int(os.getenv("FINANCIAL_HEALTH_ACTIVITY_SYNC_BONUS", "5"))
    
    # Cash flow thresholds (in cents)
    FINANCIAL_HEALTH_CASH_FLOW_POSITIVE_FLOW_BONUS: int = int(os.getenv("FINANCIAL_HEALTH_CASH_FLOW_POSITIVE_FLOW_BONUS", "15"))
    FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_THRESHOLD: int = int(os.getenv("FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_THRESHOLD", "50000"))
    FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_CASH_FLOW_HIGH_SPENDING_PENALTY", "25"))
    
    # Debt thresholds
    FINANCIAL_HEALTH_DEBT_HIGH_DEBT_RATIO: float = float(os.getenv("FINANCIAL_HEALTH_DEBT_HIGH_DEBT_RATIO", "0.5"))
    FINANCIAL_HEALTH_DEBT_HIGH_DEBT_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_DEBT_HIGH_DEBT_PENALTY", "30"))
    FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_RATIO: float = float(os.getenv("FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_RATIO", "0.3"))
    FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_DEBT_MODERATE_DEBT_PENALTY", "15"))
    
    # Investment thresholds
    FINANCIAL_HEALTH_INVESTMENT_MIN_INVESTMENT_RATIO: float = float(os.getenv("FINANCIAL_HEALTH_INVESTMENT_MIN_INVESTMENT_RATIO", "0.1"))
    FINANCIAL_HEALTH_INVESTMENT_MIN_LIQUID_FOR_INVESTMENT: int = int(os.getenv("FINANCIAL_HEALTH_INVESTMENT_MIN_LIQUID_FOR_INVESTMENT", "100000"))
    FINANCIAL_HEALTH_INVESTMENT_LOW_INVESTMENT_PENALTY: int = int(os.getenv("FINANCIAL_HEALTH_INVESTMENT_LOW_INVESTMENT_PENALTY", "20"))
    FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_RATIO: float = float(os.getenv("FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_RATIO", "0.3"))
    FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_BONUS: int = int(os.getenv("FINANCIAL_HEALTH_INVESTMENT_GOOD_INVESTMENT_BONUS", "10"))
    
    # Scoring parameters
    FINANCIAL_HEALTH_SCORING_BASE_SCORE: int = int(os.getenv("FINANCIAL_HEALTH_SCORING_BASE_SCORE", "100"))
    FINANCIAL_HEALTH_SCORING_USER_BASE_SCORE: int = int(os.getenv("FINANCIAL_HEALTH_SCORING_USER_BASE_SCORE", "70"))
    
    
    # Plaid Configuration
    PLAID_CLIENT_ID: str = os.getenv("PLAID_CLIENT_ID", "")
    PLAID_SECRET: str = os.getenv("PLAID_SECRET", "")
    PLAID_ENV: str = os.getenv("PLAID_ENV", "sandbox")
    PLAID_PRODUCTS: str = os.getenv("PLAID_PRODUCTS", "transactions,accounts,liabilities")
    PLAID_COUNTRY_CODES: str = os.getenv("PLAID_COUNTRY_CODES", "US")
    
    
    

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_required_settings()
    
    def validate_required_settings(self):
        """Validate that all required settings are provided"""
        if self.is_production:
            required_fields = ["SECRET_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_WEBHOOK_SECRET"]
            missing_fields = []
            
            for field in required_fields:
                value = getattr(self, field, None)
                if not value or (isinstance(value, str) and (value.startswith("your-") or len(value.strip()) == 0)):
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required environment variables for production: {', '.join(missing_fields)}")
        
        # For development, warn if critical secrets are missing but don't fail
        if self.is_development:
            critical_fields = ["SECRET_KEY"]
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
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    @property
    def financial_health_config(self) -> 'FinancialHealthConfig':
        """Build financial health configuration from environment variables"""
        try:
            from app.schemas.financial_health_config import FinancialHealthConfig, DEFAULT_FINANCIAL_HEALTH_CONFIG
            
            # Collect all financial health related env vars
            env_dict = {}
            for attr_name in dir(self):
                if attr_name.startswith('FINANCIAL_HEALTH_'):
                    env_dict[attr_name] = getattr(self, attr_name)
            
            # Convert to nested configuration structure
            config_data = {}
            for env_key, value in env_dict.items():
                # Remove FINANCIAL_HEALTH_ prefix and split by underscores
                parts = env_key.replace('FINANCIAL_HEALTH_', '').lower().split('_')
                
                # Build nested structure
                current = config_data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            
            return FinancialHealthConfig(**config_data)
        except Exception as e:
            # If configuration fails, return default configuration
            import warnings
            from app.schemas.financial_health_config import DEFAULT_FINANCIAL_HEALTH_CONFIG
            warnings.warn(f"Failed to build financial health config from environment: {e}. Using defaults.")
            return DEFAULT_FINANCIAL_HEALTH_CONFIG

# Create settings instance
settings = Settings()