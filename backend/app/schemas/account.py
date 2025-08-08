from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from datetime import datetime
from uuid import UUID

if TYPE_CHECKING:
    from app.schemas.transaction import TransactionResponse


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    account_type: str = Field(..., min_length=1, max_length=50)
    balance_cents: int = Field(default=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = Field(default=True)
    sync_frequency: str = Field(default="manual")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        if v not in ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']:  # Add more as needed
            raise ValueError('Invalid currency code')
        return v.upper()


class AccountCreate(AccountBase):
    user_id: UUID
    
    # Plaid Integration Fields (optional for manual accounts)
    plaid_account_id: Optional[str] = None
    plaid_access_token: Optional[str] = None
    plaid_item_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    
    # Account metadata and sync status
    account_metadata: Optional[Dict[str, Any]] = None
    sync_status: str = Field(default="manual")
    last_sync_error: Optional[str] = None
    
    # Connection health tracking
    connection_health: str = Field(default="unknown")


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    account_type: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    sync_frequency: Optional[str] = None


class Account(AccountBase):
    id: UUID
    user_id: UUID
    
    # Plaid Integration Fields
    plaid_account_id: Optional[str] = None
    plaid_item_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    
    # Account metadata and sync status
    account_metadata: Optional[Dict[str, Any]] = None
    sync_status: str = Field(default="manual")
    last_sync_error: Optional[str] = None
    
    # Connection health tracking
    connection_health: str = Field(default="unknown")
    
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

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
    last_sync: Optional[datetime] = None


class AccountListResponse(BaseModel):
    accounts: list[Account]
    summary: AccountSummary


class AccountWithTransactions(Account):
    """Account schema with transaction history"""
    
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    transaction_count: int = 0
    recent_transaction_date: Optional[datetime] = None