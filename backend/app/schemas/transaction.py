from uuid import UUID
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

class TransactionGroupBy(str, Enum):
    NONE = "none"
    DATE = "date"
    CATEGORY = "category"
    MERCHANT = "merchant"

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
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata in JSON format")
    
    # Plaid-specific fields
    plaid_transaction_id: Optional[str] = Field(None, description="Plaid transaction ID")
    plaid_category: Optional[List[str]] = Field(None, description="Plaid category")
    
    # Additional date fields
    authorized_date: Optional[date] = Field(None, description="Authorization date")
    
    # Merchant logo
    merchant_logo: Optional[str] = Field(None, description="Merchant logo URL")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        if len(v) != 3:
            raise ValueError('Currency must be a 3-letter code')
        return v.upper()

class TransactionCreate(TransactionBase):
    # Optional fields that can be provided instead of the base fields
    amount: Optional[float] = Field(None, description="Transaction amount in dollars (will be converted to cents)")
    transaction_type: Optional[str] = Field(None, description="Transaction type: 'income' or 'expense'")
    
    @model_validator(mode='before')
    @classmethod
    def convert_amount_to_cents(cls, data):
        # If this is not a dict, return as-is
        if not isinstance(data, dict):
            return data
        
        # If amount_cents is already provided, use it directly
        if 'amount_cents' in data and data['amount_cents'] is not None:
            return data
        
        # If 'amount' is provided, convert to cents
        if 'amount' in data and data['amount'] is not None:
            amount_dollars = float(data['amount'])
            amount_cents = int(amount_dollars * 100)
            
            # Apply transaction_type logic
            transaction_type = data.get('transaction_type', 'expense')
            if transaction_type == 'expense':
                # Expenses should be negative
                data['amount_cents'] = -abs(amount_cents)
            else:
                # Income should be positive  
                data['amount_cents'] = abs(amount_cents)
        
        return data

    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case

class TransactionUpdate(BaseModel):
    account_id: Optional[UUID] = Field(None, alias="accountId")
    amount_cents: Optional[int] = Field(None, alias="amountCents")
    currency: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    transaction_date: Optional[date] = Field(None, alias="transactionDate")
    category_id: Optional[UUID] = Field(None, alias="categoryId")
    status: Optional[TransactionStatus] = None
    is_recurring: Optional[bool] = Field(None, alias="isRecurring")
    is_transfer: Optional[bool] = Field(None, alias="isTransfer")
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case

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
    group_by: Optional[TransactionGroupBy] = Field(None, description="Group transactions by field")

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
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")