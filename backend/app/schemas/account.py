from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Dict, Any, TYPE_CHECKING, List
from datetime import datetime
from uuid import UUID
from enum import Enum

from .base import BaseResponseSchema
from .validation_types import CurrencyCode


class AccountType(str, Enum):
    """Account type enumeration"""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER = "other"


class SyncFrequency(str, Enum):
    """Sync frequency enumeration"""
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SyncStatus(str, Enum):
    """Sync status enumeration"""
    MANUAL = "manual"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    STALE = "stale"


class ConnectionHealth(str, Enum):
    """Connection health enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    UNKNOWN = "unknown"
    REQUIRES_UPDATE = "requires_update"


class PlaidAccountMetadata(BaseModel):
    """Schema for Plaid-specific account metadata"""
    subtype: str | None = Field(None, description="Plaid account subtype")
    mask: str | None = Field(None, description="Account number mask")
    institution_name: str | None = Field(None, description="Financial institution name")
    institution_id: str | None = Field(None, description="Plaid institution ID")
    verification_status: str | None = Field(None, description="Account verification status")
    available_balance_cents: int | None = Field(None, description="Available balance in cents")
    current_balance_cents: int | None = Field(None, description="Current balance in cents")
    iso_currency_code: str | None = Field(None, description="ISO currency code")
    unofficial_currency_code: str | None = Field(None, description="Unofficial currency code")
    
    @field_validator('available_balance_cents', 'current_balance_cents')
    @classmethod
    def validate_balance_amounts(cls, v):
        if v is not None and not isinstance(v, int):
            raise ValueError('Balance amounts must be integers (cents)')
        return v

if TYPE_CHECKING:
    from app.schemas.transaction import TransactionResponse


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    account_type: AccountType = Field(..., description="Type of account")
    balance_cents: int = Field(default=0)
    currency: CurrencyCode = Field(default="USD", description="Account currency")
    is_active: bool = Field(default=True)
    sync_frequency: SyncFrequency = Field(default=SyncFrequency.MANUAL, description="How often to sync this account")


class AccountCreate(AccountBase):
    user_id: UUID
    
    # Plaid Integration Fields (optional for manual accounts)
    plaid_account_id: str | None = None
    plaid_item_id: str | None = None
    last_sync_at: datetime | None = None
    
    # Account metadata and sync status
    account_metadata: PlaidAccountMetadata | None = None
    sync_status: SyncStatus = Field(default=SyncStatus.MANUAL, description="Current sync status")
    last_sync_error: str | None = None
    
    # Connection health tracking
    connection_health: ConnectionHealth = Field(default=ConnectionHealth.UNKNOWN, description="Connection health status")


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    account_type: AccountType | None = None
    is_active: bool | None = None
    sync_frequency: SyncFrequency | None = None


class Account(AccountBase, BaseResponseSchema):
    user_id: UUID
    
    # Plaid Integration Fields
    plaid_account_id: str | None = None
    plaid_item_id: str | None = None
    last_sync_at: datetime | None = None
    
    # Account metadata and sync status
    account_metadata: PlaidAccountMetadata | None = None
    sync_status: SyncStatus = Field(default=SyncStatus.MANUAL, description="Current sync status")
    last_sync_error: str | None = None
    
    # Connection health tracking
    connection_health: ConnectionHealth = Field(default=ConnectionHealth.UNKNOWN, description="Connection health status")

    @property
    def balance_dollars(self) -> float:
        """Convert balance from cents to dollars"""
        return self.balance_cents / 100.0

    @property
    def is_plaid_connected(self) -> bool:
        """Check if account is connected to Plaid"""
        return bool(self.plaid_account_id)


class AccountSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    total_balance_cents: int
    by_type: Dict[str, Dict[str, int]]  # account_type -> {count, balance_cents}
    plaid_connected: int
    last_sync: datetime | None = None


class AccountListResponse(BaseModel):
    accounts: list[Account]
    summary: AccountSummary


class AccountWithTransactions(Account):
    """Account schema with transaction history"""
    
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    transaction_count: int = 0
    recent_transaction_date: datetime | None = None


# Plaid-specific response schemas

class PlaidLinkTokenResponse(BaseModel):
    """Response schema for Plaid link token creation"""
    link_token: str = Field(..., description="Plaid link token")
    expiration: datetime | None = Field(None, description="Token expiration")
    request_id: str | None = Field(None, description="Plaid request ID")


class PlaidAccountInfo(BaseModel):
    """Schema for account information in Plaid responses"""
    id: UUID = Field(..., description="Account ID")
    name: str = Field(..., description="Account name")
    type: str = Field(..., description="Account type")
    balance: float = Field(..., description="Account balance in dollars")
    currency: str = Field(default="USD", description="Account currency")


class PlaidInstitutionInfo(BaseModel):
    """Schema for institution information in Plaid responses"""
    name: str = Field(..., description="Institution name")
    institution_id: str | None = Field(None, description="Plaid institution ID")


class PlaidExchangeTokenResponse(BaseModel):
    """Response schema for Plaid public token exchange"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Dict[str, Any] = Field(..., description="Response data")
    
    class Config:
        extra = "allow"


class PlaidConnectionStatusData(BaseModel):
    """Schema for Plaid connection status data"""
    connected_accounts: int = Field(..., description="Number of connected accounts")
    last_sync: datetime | None = Field(None, description="Last successful sync")
    health_status: str = Field(..., description="Overall connection health")
    accounts: List[PlaidAccountInfo] = Field(default_factory=list, description="Account details")


class PlaidConnectionStatusResponse(BaseModel):
    """Response schema for Plaid connection status"""
    success: bool = Field(..., description="Whether the operation was successful")
    data: PlaidConnectionStatusData = Field(..., description="Connection status data")


class PlaidOperationResponse(BaseModel):
    """Generic response schema for Plaid operations (update-mode, disconnect, etc.)"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    account_id: UUID | None = Field(None, description="Affected account ID")
    
    class Config:
        extra = "allow"