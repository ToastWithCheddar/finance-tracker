from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid

class UserPreferencesBase(BaseModel):
    # Display preferences
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    date_format: str = Field(default="MM/DD/YYYY", max_length=20, description="Date display format")
    number_format: str = Field(default="en-US", max_length=20, description="Number locale format")
    theme: str = Field(default="light", pattern="^(light|dark|auto)$", description="UI theme")
    
    # Notification preferences
    email_notifications: bool = Field(default=True, description="Receive email notifications")
    push_notifications: bool = Field(default=True, description="Receive push notifications")
    transaction_reminders: bool = Field(default=False, description="Get transaction reminders")
    budget_alerts: bool = Field(default=True, description="Receive budget alerts")
    weekly_reports: bool = Field(default=False, description="Receive weekly reports")
    monthly_reports: bool = Field(default=True, description="Receive monthly reports")
    
    # Privacy preferences
    data_sharing: bool = Field(default=False, description="Allow data sharing for analytics")
    analytics_tracking: bool = Field(default=True, description="Allow analytics tracking")
    
    # Financial preferences
    default_account_type: str = Field(default="checking", max_length=50, description="Default account type")
    budget_warning_threshold: float = Field(default=0.8, ge=0.1, le=1.0, description="Budget warning threshold (0.1-1.0)")
    low_balance_threshold: float = Field(default=100.0, ge=0, description="Low balance alert threshold")
    
    # Backup preferences
    auto_backup: bool = Field(default=True, description="Enable automatic backups")
    backup_frequency: str = Field(default="weekly", pattern="^(daily|weekly|monthly)$", description="Backup frequency")
    
    # App preferences
    startup_page: str = Field(default="dashboard", max_length=50, description="Default startup page")
    items_per_page: int = Field(default=25, ge=10, le=100, description="Items per page for pagination")
    auto_categorize: bool = Field(default=True, description="Automatically categorize transactions")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        # Common currency codes validation
        valid_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD',
            'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW'
        ]
        if v.upper() not in valid_currencies:
            raise ValueError(f'Currency must be one of: {", ".join(valid_currencies)}')
        return v.upper()

    @field_validator('startup_page')
    @classmethod
    def validate_startup_page(cls, v):
        valid_pages = ['dashboard', 'transactions', 'budgets', 'goals', 'insights', 'accounts']
        if v not in valid_pages:
            raise ValueError(f'Startup page must be one of: {", ".join(valid_pages)}')
        return v

class UserPreferencesCreate(UserPreferencesBase):
    pass

class UserPreferencesUpdate(BaseModel):
    # All fields optional for updates
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    date_format: Optional[str] = Field(None, max_length=20)
    number_format: Optional[str] = Field(None, max_length=20)
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    transaction_reminders: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    weekly_reports: Optional[bool] = None
    monthly_reports: Optional[bool] = None
    
    data_sharing: Optional[bool] = None
    analytics_tracking: Optional[bool] = None
    
    default_account_type: Optional[str] = Field(None, max_length=50)
    budget_warning_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    low_balance_threshold: Optional[float] = Field(None, ge=0)
    
    auto_backup: Optional[bool] = None
    backup_frequency: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    
    startup_page: Optional[str] = Field(None, max_length=50)
    items_per_page: Optional[int] = Field(None, ge=10, le=100)
    auto_categorize: Optional[bool] = None

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        if v is not None:
            valid_currencies = [
                'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD',
                'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW'
            ]
            if v.upper() not in valid_currencies:
                raise ValueError(f'Currency must be one of: {", ".join(valid_currencies)}')
            return v.upper()
        return v

    @field_validator('startup_page')
    @classmethod
    def validate_startup_page(cls, v):
        if v is not None:
            valid_pages = ['dashboard', 'transactions', 'budgets', 'goals', 'insights', 'accounts']
            if v not in valid_pages:
                raise ValueError(f'Startup page must be one of: {", ".join(valid_pages)}')
        return v

class UserPreferencesInDB(UserPreferencesBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserPreferencesResponse(UserPreferencesInDB):
    pass