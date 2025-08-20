from uuid import UUID
from datetime import datetime, date
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from enum import Enum

from .base import BaseResponseSchema
from .validation_types import CurrencyCode, DateRangeValidatorMixin

class TransactionGroupBy(str, Enum):
    NONE = "none"
    DATE = "date"
    CATEGORY = "category"
    MERCHANT = "merchant"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    CANCELLED = "cancelled"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class TransactionBase(BaseModel):
    account_id: UUID = Field(..., description="Account ID")
    amount_cents: int = Field(..., description="Transaction amount in cents (can be negative for expenses)")
    currency: CurrencyCode = Field("USD", description="Currency code")
    description: str = Field(..., max_length=500, description="Transaction description")
    merchant: str | None = Field(None, max_length=200, description="Merchant name")
    transaction_date: date = Field(..., description="Transaction date")
    category_id: UUID | None = Field(None, description="Category ID")
    status: TransactionStatus = Field(TransactionStatus.POSTED, description="Transaction status")
    is_recurring: bool = Field(False, description="Is this a recurring transaction")
    is_transfer: bool = Field(False, description="Is this a transfer between accounts")
    notes: str | None = Field(None, description="Additional notes")
    tags: List[str] | None = Field(None, description="Transaction tags")
    metadata_json: Dict[str, Any] | None = Field(None, description="Additional metadata in JSON format")
    
    # Plaid-specific fields
    plaid_transaction_id: str | None = Field(None, description="Plaid transaction ID")
    plaid_category: List[str] | None = Field(None, description="Plaid category")
    
    # Additional date fields
    authorized_date: date | None = Field(None, description="Authorization date")
    
    # Merchant logo
    merchant_logo: str | None = Field(None, description="Merchant logo URL")

    @field_validator('authorized_date')
    @classmethod
    def validate_authorized_date(cls, v, info):
        if v and 'transaction_date' in info.data and info.data['transaction_date']:
            if v > info.data['transaction_date']:
                raise ValueError('Authorized date cannot be after transaction date')
        return v

    @field_validator('amount_cents')
    @classmethod
    def validate_amount_cents(cls, v):
        if v == 0:
            raise ValueError('Transaction amount cannot be zero')
        return v

    @model_validator(mode='after')
    def validate_transfer_logic(self):
        # Transfer transactions should have specific characteristics
        if self.is_transfer:
            if not self.description or 'transfer' not in self.description.lower():
                # Add transfer indicator to description if missing
                self.description = f"Transfer: {self.description or 'Account transfer'}"
            
            # Transfer transactions typically shouldn't have categories
            if self.category_id:
                raise ValueError('Transfer transactions should not have categories assigned')
                
        return self

class TransactionCreate(TransactionBase):
    # Optional fields that can be provided instead of the base fields
    amount: float | None = Field(None, description="Transaction amount in dollars (will be converted to cents)")
    transaction_type: TransactionType | None = Field(None, description="Transaction type: 'income' or 'expense'")
    
    @model_validator(mode='before')
    @classmethod
    def convert_amount_to_cents(cls, data):
        # If this is not a dict, return as-is
        if not isinstance(data, dict):
            return data
        
        # Check if both amount and amount_cents are provided - this is ambiguous
        if ('amount' in data and data['amount'] is not None and 
            'amount_cents' in data and data['amount_cents'] is not None):
            raise ValueError("Cannot provide both 'amount' and 'amount_cents'. Please use only one field to avoid ambiguity.")
        
        # If amount_cents is already provided, use it directly
        if 'amount_cents' in data and data['amount_cents'] is not None:
            return data
        
        # If 'amount' is provided, convert to cents
        if 'amount' in data and data['amount'] is not None:
            amount_dollars = float(data['amount'])
            amount_cents = int(amount_dollars * 100)
            
            # Apply transaction_type logic
            transaction_type = data.get('transaction_type', TransactionType.EXPENSE)
            if transaction_type == TransactionType.EXPENSE:
                # Expenses should be negative
                data['amount_cents'] = -abs(amount_cents)
            else:
                # Income should be positive  
                data['amount_cents'] = abs(amount_cents)
        
        return data

    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case

class TransactionUpdate(BaseModel):
    account_id: UUID | None = Field(None, alias="accountId")
    amount_cents: int | None = Field(None, alias="amountCents")
    currency: str | None = None
    description: str | None = Field(None, max_length=500)
    merchant: str | None = Field(None, max_length=200)
    transaction_date: date | None = Field(None, alias="transactionDate")
    category_id: UUID | None = Field(None, alias="categoryId")
    status: TransactionStatus | None = None
    is_recurring: bool | None = Field(None, alias="isRecurring")
    is_transfer: bool | None = Field(None, alias="isTransfer")
    notes: str | None = None
    tags: List[str] | None = None
    
    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case

class TransactionInDB(TransactionBase, BaseResponseSchema):
    user_id: UUID
    
    # Additional fields that might be set by ML or external integrations
    confidence_score: float | None = None
    ml_suggested_category_id: UUID | None = None
    plaid_transaction_id: Optional[str] = None

class TransactionResponse(TransactionInDB):
    # Include category name for convenience
    category_name: str | None = None
    account_name: str | None = None
    
    # Helper computed fields for frontend
    @computed_field
    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars for display"""
        return self.amount_cents / 100.0
        
    @computed_field
    @property
    def is_expense(self) -> bool:
        """Check if transaction is an expense (negative amount)"""
        return self.amount_cents < 0
        
    @computed_field
    @property
    def is_income(self) -> bool:
        """Check if transaction is income (positive amount)"""
        return self.amount_cents > 0

class TransactionFilter(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    status: TransactionStatus | None = None
    min_amount_cents: int | None = Field(None, description="Minimum amount in cents")
    max_amount_cents: int | None = Field(None, description="Maximum amount in cents")
    search_query: str | None = Field(None, description="Search in description or merchant")
    is_recurring: bool | None = None
    is_transfer: bool | None = None
    tags: List[str] | None = None
    group_by: TransactionGroupBy | None = Field(None, description="Group transactions by field")

    @field_validator('max_amount_cents')
    @classmethod
    def validate_max_amount(cls, v, info):
        if v is not None and info.data.get('min_amount_cents') is not None:
            if v < info.data['min_amount_cents']:
                raise ValueError('max_amount_cents must be greater than min_amount_cents')
        return v

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        if v and 'start_date' in info.data and info.data['start_date'] and v <= info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v

class TransactionPagination(BaseModel):
    limit: int = Field(25, ge=1, le=100)
    offset: int = Field(0, ge=0)

class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

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
    category: str | None = Field(None, description="Category name")
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

class TransactionGroup(BaseModel):
    """Schema for grouped transaction response"""
    key: str = Field(..., description="Group key (category name, merchant name, or date)")
    total_amount_cents: int = Field(..., description="Total amount for this group in cents")
    count: int = Field(..., description="Number of transactions in this group")
    transactions: List[TransactionResponse] = Field(..., description="Transactions in this group")

class TransactionGroupedResponse(BaseModel):
    """Schema for grouped transaction list response"""
    groups: List[TransactionGroup] = Field(..., description="Grouped transactions")
    total: int = Field(..., description="Total number of transactions across all groups")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Offset for pagination")
    has_more: bool = Field(..., description="Whether there are more results")