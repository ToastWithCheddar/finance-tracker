# Standard library imports
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, Field, validator

# Local imports
from .validation_types import (
    NonNegativeAmount, NonEmptyStringList, TagList, 
    TransactionTypeField, UUIDList, ConfidenceScore
)


# Strongly typed models for rule conditions and actions
class AmountRange(BaseModel):
    """Schema for amount range conditions"""
    min_cents: NonNegativeAmount = Field(None, description="Minimum amount in cents")
    max_cents: NonNegativeAmount = Field(None, description="Maximum amount in cents")
    
    @validator('max_cents')
    def validate_max_greater_than_min(cls, v, values):
        if v is not None and 'min_cents' in values and values['min_cents'] is not None:
            if v <= values['min_cents']:
                raise ValueError('max_cents must be greater than min_cents')
        return v


class RuleConditions(BaseModel):
    """Strongly typed schema for rule conditions"""
    merchant_contains: NonEmptyStringList = Field(None, description="Merchant name contains any of these strings")
    description_contains: NonEmptyStringList = Field(None, description="Transaction description contains any of these strings")
    amount_range: AmountRange | None = Field(None, description="Amount range filter")
    account_types: NonEmptyStringList = Field(None, description="Account types to match")
    transaction_type: TransactionTypeField = Field(None, description="Transaction type (debit/credit)")
    account_ids: UUIDList = Field(None, description="Specific account IDs to match")
    category_not_in: UUIDList = Field(None, description="Categories to exclude")


class RuleActions(BaseModel):
    """Strongly typed schema for rule actions"""
    set_category_id: UUID | None = Field(None, description="Category ID to assign")
    add_tags: TagList = Field(None, description="Tags to add to transaction")
    set_confidence: ConfidenceScore | None = Field(None, description="Confidence score (0-1)")
    add_note: str | None = Field(None, max_length=500, description="Note to add to transaction")

class CategorizationRuleCreate(BaseModel):
    """Schema for creating a categorization rule"""
    
    name: str = Field(..., min_length=1, max_length=200, description="Name of the rule")
    description: str | None = Field(None, max_length=1000, description="Description of the rule")
    priority: int = Field(default=100, ge=1, le=1000, description="Rule priority (lower = higher priority)")
    conditions: RuleConditions = Field(..., description="Conditions for matching transactions")
    actions: RuleActions = Field(..., description="Actions to perform when rule matches")
    template_id: UUID | None = Field(None, description="ID of template used to create this rule")
    template_version: str | None = Field(None, description="Version of template used")
    is_active: bool = Field(default=True, description="Whether the rule is active")
    
    @validator('conditions')
    def validate_conditions_not_empty(cls, v):
        """Ensure at least one condition is specified"""
        if not any([v.merchant_contains, v.description_contains, v.amount_range, 
                   v.account_types, v.transaction_type, v.account_ids, v.category_not_in]):
            raise ValueError('At least one condition must be specified')
        return v
    
    @validator('actions')
    def validate_actions_not_empty(cls, v):
        """Ensure at least one action is specified"""
        if not any([v.set_category_id, v.add_tags, v.set_confidence, v.add_note]):
            raise ValueError('At least one action must be specified')
        return v

class CategorizationRuleUpdate(BaseModel):
    """Schema for updating a categorization rule"""
    
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    priority: int | None = Field(None, ge=1, le=1000)
    conditions: RuleConditions | None = None
    actions: RuleActions | None = None
    is_active: bool | None = None

class CategorizationRuleResponse(BaseModel):
    """Response schema for categorization rules"""
    
    id: UUID
    name: str
    description: str | None = None
    priority: int
    is_active: bool
    conditions: RuleConditions
    actions: RuleActions
    times_applied: int
    success_rate: float | None = None
    success_rate_percentage: float | None = None
    last_applied_at: datetime | None = None
    template_id: UUID | None = None
    template_version: str | None = None
    is_from_template: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CategorizationRuleFilter(BaseModel):
    """Schema for filtering categorization rules"""
    
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    is_active: bool | None = None
    search: str | None = Field(None, max_length=200)
    priority_min: int | None = Field(None, ge=1)
    priority_max: int | None = Field(None, le=1000)
    template_id: UUID | None = None

class PaginatedCategorizationRulesResponse(BaseModel):
    """Paginated response for categorization rules"""
    
    items: List[CategorizationRuleResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class RuleTestRequest(BaseModel):
    """Request schema for testing rule conditions"""
    
    conditions: RuleConditions = Field(..., description="Rule conditions to test")
    limit: int = Field(default=100, ge=1, le=500, description="Number of transactions to test against")
    
    @validator('conditions')
    def validate_conditions_not_empty(cls, v):
        """Ensure at least one condition is specified for testing"""
        if not any([v.merchant_contains, v.description_contains, v.amount_range, 
                   v.account_types, v.transaction_type, v.account_ids, v.category_not_in]):
            raise ValueError('At least one condition must be specified for testing')
        return v

class RuleTestResponse(BaseModel):
    """Response schema for rule testing"""
    
    rule_id: UUID | None = None
    rule_name: str | None = None
    conditions: RuleConditions | None = None
    total_matches: int
    matching_transactions: List[Dict[str, Any]]

class RuleApplicationRequest(BaseModel):
    """Request schema for applying rules to transactions"""
    
    transaction_ids: List[UUID] = Field(..., min_items=1, description="List of transaction IDs")
    dry_run: bool = Field(default=False, description="Preview changes without applying them")

class RuleApplicationResponse(BaseModel):
    """Response schema for rule application"""
    
    success: bool
    transactions_processed: int
    rules_applied: int
    results: List[Dict[str, Any]]
    dry_run: bool
    error: str | None = None

class RuleEffectivenessResponse(BaseModel):
    """Response schema for rule effectiveness metrics"""
    
    rule_id: UUID
    rule_name: str
    times_applied: int
    success_rate: float | None = None
    success_rate_percentage: float | None = None
    last_applied_at: datetime | None = None
    is_active: bool
    priority: int

class RuleStatisticsResponse(BaseModel):
    """Response schema for rule statistics"""
    
    total_rules: int
    active_rules: int
    total_applications: int
    rules_never_used: int
    average_success_rate: float
    average_success_rate_percentage: float
    most_used_rule: Dict[str, Any] | None = None

class RuleFeedbackRequest(BaseModel):
    """Request schema for providing rule feedback"""
    
    success: bool = Field(..., description="Whether the rule application was successful")

class RuleFeedbackResponse(BaseModel):
    """Response schema for rule feedback"""
    
    success: bool
    rule_id: UUID
    new_success_rate: float | None = None
    new_success_rate_percentage: float | None = None

# Template-related schemas

class RuleTemplateResponse(BaseModel):
    """Response schema for rule templates"""
    
    id: UUID
    name: str
    description: str
    category: str
    conditions_template: RuleConditions
    actions_template: RuleActions
    popularity_score: int
    times_used: int
    success_rating: float | None = None
    success_rating_percentage: float | None = None
    is_official: bool
    is_community_template: bool
    default_priority: int
    tags: List[str] | None = None
    required_customizations: List[str]
    version: str
    
    class Config:
        from_attributes = True

class RuleTemplateCustomization(BaseModel):
    """Schema for template customizations"""
    
    name: str | None = Field(None, description="Custom name for the rule")
    target_category_id: UUID | None = Field(None, description="Target category ID")
    # Add other customization fields as needed
    
    class Config:
        extra = "allow"  # Allow additional customization fields

class RuleTemplateCreateRequest(BaseModel):
    """Request schema for creating a rule from template"""
    
    customizations: RuleTemplateCustomization = Field(..., description="Template customizations")

class RuleTemplateCreateResponse(BaseModel):
    """Response schema for creating a rule from template"""
    
    success: bool
    rule_id: UUID
    rule_name: str
    template_id: UUID
    created_at: datetime

class RuleTemplateFilter(BaseModel):
    """Schema for filtering rule templates"""
    
    category_filter: str | None = None
    official_only: bool = False
    limit: int = Field(default=50, ge=1, le=100)