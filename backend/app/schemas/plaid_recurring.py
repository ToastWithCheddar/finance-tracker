# Standard library imports
from datetime import date, datetime
from typing import List, Dict, Any
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, Field, validator

# Local imports
from .validation_types import (
    PlaidRecurringStatus, PlaidRecurringFrequency, ConfidenceScore
)

class PlaidRecurringTransactionResponse(BaseModel):
    """Response schema for Plaid recurring transactions"""
    
    plaid_recurring_transaction_id: str
    description: str
    merchant_name: str | None = None
    amount_cents: int
    amount_dollars: float
    currency: str
    frequency: str
    status: str
    category: List[str] | None = None
    last_amount_cents: int | None = None
    last_amount_dollars: float | None = None
    last_date: str | None = None  # ISO format date string
    monthly_estimated_cents: int
    monthly_estimated_dollars: float
    account_id: UUID
    is_muted: bool
    is_linked_to_rule: bool
    linked_rule_id: UUID | None = None
    is_mature: bool
    first_detected_at: datetime
    last_sync_at: datetime
    sync_count: int
    
    class Config:
        from_attributes = True

class PlaidRecurringSyncRequest(BaseModel):
    """Request schema for manually syncing Plaid recurring transactions"""
    
    force_sync: bool = Field(default=False, description="Force sync even if recently synced")

class PlaidRecurringSyncResponse(BaseModel):
    """Response schema for Plaid recurring transaction sync"""
    
    success: bool
    accounts_processed: int
    total_recurring_transactions: int
    new_recurring_transactions: int
    updated_recurring_transactions: int
    total_errors: int
    results: List[Dict[str, Any]]
    message: str | None = None
    error: str | None = None

class PlaidRecurringMuteRequest(BaseModel):
    """Request schema for muting/unmuting Plaid recurring transactions"""
    
    muted: bool = Field(..., description="Whether to mute the recurring transaction")

class PlaidRecurringMuteResponse(BaseModel):
    """Response schema for muting/unmuting Plaid recurring transactions"""
    
    success: bool
    plaid_recurring_transaction_id: str
    is_muted: bool
    action: str  # "muted" or "unmuted"

class PlaidRecurringLinkRequest(BaseModel):
    """Request schema for linking Plaid recurring transaction to rule"""
    
    rule_id: UUID = Field(..., description="ID of the recurring transaction rule to link to")

class PlaidRecurringLinkResponse(BaseModel):
    """Response schema for linking Plaid recurring transaction to rule"""
    
    success: bool
    plaid_recurring_transaction_id: str
    linked_rule_id: UUID
    linked_rule_name: str
    is_linked_to_rule: bool

class PlaidRecurringUnlinkResponse(BaseModel):
    """Response schema for unlinking Plaid recurring transaction from rule"""
    
    success: bool
    plaid_recurring_transaction_id: str
    is_linked_to_rule: bool

class PlaidRecurringPotentialMatch(BaseModel):
    """Schema for potential rule matches"""
    
    rule_id: UUID
    name: str
    description: str | None = None
    amount_cents: int
    amount_dollars: float
    frequency: str
    interval: int
    is_active: bool
    confidence_score: ConfidenceScore | None = None

class PlaidRecurringInsightsResponse(BaseModel):
    """Response schema for recurring transaction insights"""
    
    total_subscriptions: int
    total_monthly_cost_cents: int
    total_monthly_cost_dollars: float
    active_subscriptions: int
    muted_subscriptions: int
    linked_subscriptions: int
    mature_subscriptions: int
    frequency_breakdown: Dict[str, int]
    status_breakdown: Dict[str, int]
    top_subscriptions: List[Dict[str, Any]]
    cost_by_account: Dict[str, Dict[str, Any]]

class PlaidRecurringBulkMuteRequest(BaseModel):
    """Request schema for bulk muting/unmuting Plaid recurring transactions"""
    
    plaid_recurring_ids: List[str] = Field(..., min_items=1, description="List of Plaid recurring transaction IDs")
    muted: bool = Field(..., description="Whether to mute the recurring transactions")

class PlaidRecurringBulkMuteResponse(BaseModel):
    """Response schema for bulk muting/unmuting operations"""
    
    updated_count: int
    failed_count: int
    failed_ids: List[str]
    action: str  # "muted" or "unmuted"

class PlaidRecurringFilter(BaseModel):
    """Schema for filtering Plaid recurring transactions"""
    
    include_muted: bool = False
    account_id: UUID | None = None
    status_filter: PlaidRecurringStatus | None = None
    frequency_filter: PlaidRecurringFrequency | None = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)