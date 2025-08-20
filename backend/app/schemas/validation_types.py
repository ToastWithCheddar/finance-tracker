# Standard library imports
from enum import Enum
from typing import Annotated, List, Optional

# Third-party imports
from pydantic import Field, BeforeValidator, field_validator
from pydantic.functional_validators import BeforeValidator


# Color validation
def _normalize_hex_color(v):
    """Normalize hex color by adding # prefix if missing"""
    if v and not v.startswith('#'):
        return f"#{v}"
    return v


def _validate_non_negative_amount(v):
    """Validate that amount is non-negative"""
    if v is not None and v < 0:
        raise ValueError('Amount must be non-negative')
    return v


def _validate_positive_amount(v):
    """Validate that amount is positive"""
    if v is not None and v <= 0:
        raise ValueError('Amount must be positive')
    return v


def _validate_currency_code(v):
    """Validate and normalize currency code"""
    if v is not None:
        if len(v) != 3:
            raise ValueError('Currency must be a 3-letter code')
        return v.upper()
    return v


def _validate_confidence_score(v):
    """Validate confidence score is between 0.0 and 1.0"""
    if v is not None:
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
    return v


def _validate_non_empty_string_list(v):
    """Validate that string list is not empty and contains valid strings"""
    if v is not None:
        if not v:  # Empty list
            raise ValueError('String list cannot be empty if provided')
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError('All items must be non-empty strings')
    return v


def _validate_tag_list(v):
    """Validate tag list with specific constraints"""
    if v is not None:
        if not v:  # Empty list
            raise ValueError('Tags list cannot be empty if provided')
        for tag in v:
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError('All tags must be non-empty strings')
            if len(tag) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
    return v


def _validate_uuid_list(v):
    """Validate UUID list is not empty if provided"""
    if v is not None and len(v) == 0:
        raise ValueError('UUID list cannot be empty if provided')
    return v


# Transaction Types Enum
class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


def _validate_transaction_type(v):
    """Validate transaction type"""
    if v is not None and v not in ['debit', 'credit']:
        raise ValueError('transaction_type must be "debit" or "credit"')
    return v


# Annotated types for reuse across schemas
HexColor = Annotated[
    Optional[str], 
    Field(pattern=r"^#[0-9A-Fa-f]{6}$"),
    BeforeValidator(_normalize_hex_color)
]

NonNegativeAmount = Annotated[
    Optional[int],
    BeforeValidator(_validate_non_negative_amount)
]

PositiveAmount = Annotated[
    int,
    BeforeValidator(_validate_positive_amount)
]

CurrencyCode = Annotated[
    str,
    BeforeValidator(_validate_currency_code)
]

ConfidenceScore = Annotated[
    float,
    Field(ge=0.0, le=1.0),
    BeforeValidator(_validate_confidence_score)
]

NonEmptyStringList = Annotated[
    Optional[List[str]],
    BeforeValidator(_validate_non_empty_string_list)
]

TagList = Annotated[
    Optional[List[str]],
    BeforeValidator(_validate_tag_list)
]

UUIDList = Annotated[
    Optional[List],
    BeforeValidator(_validate_uuid_list)
]

TransactionTypeField = Annotated[
    Optional[str],
    BeforeValidator(_validate_transaction_type)
]


# Common validation mixins for complex scenarios
class DateRangeValidatorMixin:
    """Mixin for schemas that need start_date/end_date validation"""
    
    @field_validator('end_date')
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Validate that end_date is after start_date"""
        start_field_names = ['start_date', 'date_from', 'from_date']
        start_date = None
        
        # Find start date field with flexible naming
        for field_name in start_field_names:
            if field_name in info.data and info.data[field_name] is not None:
                start_date = info.data[field_name]
                break
        
        if v is not None and start_date is not None:
            if v <= start_date:
                raise ValueError('End date must be after start date')
        return v


# Plaid-specific enums for type safety
class PlaidRecurringStatus(str, Enum):
    MATURE = "MATURE"
    EARLY_DETECTION = "EARLY_DETECTION"
    UNKNOWN = "UNKNOWN"


class PlaidRecurringFrequency(str, Enum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"
    UNKNOWN = "UNKNOWN"


# Account-specific enums
class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER = "other"


class SyncStatus(str, Enum):
    MANUAL = "manual"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ConnectionHealth(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class SyncFrequency(str, Enum):
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"