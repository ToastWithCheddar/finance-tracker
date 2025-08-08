from uuid import UUID
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class TransactionStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    CANCELLED = "cancelled"

class TransactionBase(BaseModel):
    account_id: UUID = Field(..., description="Account ID")
    amount_cents: int = Field(..., description="Transaction amount in cents (can be negative for expenses)")
    currency: str = Field("USD", description="Currency code")
    description: str = Field(..., max_length=500, description="Transaction description")
    merchant: Optional[str] = Field(None, max_length=200, description="Merchant name")
    transaction_date: date = Field(..., description="Transaction date")
    category_id: Optional[UUID] = Field(None, description="Category ID")
    status: TransactionStatus = Field(TransactionStatus.POSTED, description="Transaction status")
    is_recurring: bool = Field(False, description="Is this a recurring transaction")
    is_transfer: bool = Field(False, description="Is this a transfer between accounts")
    notes: Optional[str] = Field(None, description="Additional notes")
    tags: Optional[List[str]] = Field(None, description="Transaction tags")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        if len(v) != 3:
            raise ValueError('Currency must be a 3-letter code')
        return v.upper()

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    account_id: Optional[UUID] = None
    amount_cents: Optional[int] = None
    currency: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    transaction_date: Optional[date] = None
    category_id: Optional[UUID] = None
    status: Optional[TransactionStatus] = None
    is_recurring: Optional[bool] = None
    is_transfer: Optional[bool] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class TransactionInDB(TransactionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Additional fields that might be set by ML or external integrations
    confidence_score: Optional[float] = None
    ml_suggested_category_id: Optional[UUID] = None
    plaid_transaction_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class TransactionResponse(TransactionInDB):
    # Include category name for convenience
    category_name: Optional[str] = None
    account_name: Optional[str] = None
    
    # Helper properties for frontend
    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars for display"""
        return self.amount_cents / 100.0
        
    @property
    def is_expense(self) -> bool:
        """Check if transaction is an expense (negative amount)"""
        return self.amount_cents < 0
        
    @property
    def is_income(self) -> bool:
        """Check if transaction is income (positive amount)"""
        return self.amount_cents > 0

class TransactionFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    status: Optional[TransactionStatus] = None
    min_amount_cents: Optional[int] = Field(None, description="Minimum amount in cents")
    max_amount_cents: Optional[int] = Field(None, description="Maximum amount in cents")
    search_query: Optional[str] = Field(None, description="Search in description or merchant")
    is_recurring: Optional[bool] = None
    is_transfer: Optional[bool] = None
    tags: Optional[List[str]] = None

    @field_validator('max_amount_cents')
    @classmethod
    def validate_max_amount(cls, v, values):
        if v is not None and values.data.get('min_amount_cents') is not None:
            if v < values.data['min_amount_cents']:
                raise ValueError('max_amount_cents must be greater than min_amount_cents')
        return v

class TransactionPagination(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(25, ge=1, le=100)

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class TransactionStats(BaseModel):
    total_income_cents: int
    total_expenses_cents: int
    net_amount_cents: int
    transaction_count: int
    average_transaction_cents: int
    
class TransactionCSVImport(BaseModel):
    """Schema for CSV import data"""
    date: str = Field(..., description="Transaction date (YYYY-MM-DD format)")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Amount (will be converted to cents)")
    category: Optional[str] = Field(None, description="Category name")
    account: str = Field(..., description="Account name")
    
    @field_validator('amount')
    @classmethod
    def convert_to_cents(cls, v):
        # Convert dollars to cents
        return int(v * 100)

class TransactionBulkCreate(BaseModel):
    """Schema for bulk transaction creation"""
    transactions: List[TransactionCreate] = Field(..., max_items=1000)
    
class TransactionBulkUpdate(BaseModel):
    """Schema for bulk transaction updates"""
    transaction_ids: List[UUID] = Field(..., min_items=1, max_items=1000)
    updates: TransactionUpdate