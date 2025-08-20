"""
Account Health Schemas
Pydantic models for account health responses and related data structures
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class ReconciliationHealth(BaseModel):
    """Reconciliation health information"""
    model_config = ConfigDict(from_attributes=True)
    
    is_reconciled: bool
    discrepancy: float
    last_reconciliation: Optional[datetime]
    transaction_count: int


class ConnectionHealth(BaseModel):
    """Account connection health information"""
    model_config = ConfigDict(from_attributes=True)
    
    health_status: str  # "healthy", "warning", "failed", "not_connected"
    is_plaid_connected: bool
    last_sync: Optional[str]
    sync_frequency: Optional[str]  # "daily", "weekly", "stale"


class AccountHealthData(BaseModel):
    """Detailed account health data"""
    model_config = ConfigDict(from_attributes=True)
    
    account_id: UUID
    account_name: str
    account_type: str
    is_active: bool
    current_balance: float
    currency: str
    
    # Health components
    reconciliation: ReconciliationHealth
    connection: ConnectionHealth
    
    # Overall metrics
    health_score: int  # 0-100
    recommendations: List[str]


class AccountHealthResponse(BaseModel):
    """Account health endpoint response"""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    data: AccountHealthData