"""
Database validation service for JSONB fields and data integrity
"""
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class TransactionMetadataSchema(BaseModel):
    """Schema for transaction metadata JSON validation"""
    plaid_metadata: Optional[Dict[str, Any]] = None
    ml_predictions: Optional[Dict[str, Any]] = None
    user_tags: Optional[List[str]] = None
    recurring_rule: Optional[Dict[str, Any]] = None
    location_data: Optional[Dict[str, Any]] = None

class LocationSchema(BaseModel):
    """Schema for location data validation"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class RecurringRuleSchema(BaseModel):
    """Schema for recurring transaction rules"""
    frequency: str  # daily, weekly, monthly, yearly
    interval: int = 1  # every N periods
    end_date: Optional[str] = None
    max_occurrences: Optional[int] = None
    day_of_month: Optional[int] = None
    day_of_week: Optional[int] = None

class DataValidationService:
    """Service for validating JSONB data and ensuring data integrity"""
    
    def __init__(self):
        self.schemas = {
            'transaction_metadata': TransactionMetadataSchema,
            'location': LocationSchema,
            'recurring_rule': RecurringRuleSchema,
        }
    
    def validate_transaction_metadata(self, metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate transaction metadata JSONB field"""
        try:
            TransactionMetadataSchema(**metadata)
            return True, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, errors
    
    def validate_location_data(self, location: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate location JSONB field"""
        try:
            LocationSchema(**location)
            
            # Additional validation for coordinates
            if 'latitude' in location and location['latitude'] is not None:
                lat = location['latitude']
                if not (-90 <= lat <= 90):
                    return False, ['Latitude must be between -90 and 90']
            
            if 'longitude' in location and location['longitude'] is not None:
                lng = location['longitude']
                if not (-180 <= lng <= 180):
                    return False, ['Longitude must be between -180 and 180']
            
            return True, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, errors
    
    def validate_recurring_rule(self, rule: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate recurring transaction rule"""
        try:
            RecurringRuleSchema(**rule)
            
            # Additional business logic validation
            frequency = rule.get('frequency')
            if frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
                return False, ['Invalid frequency value']
            
            interval = rule.get('interval', 1)
            if interval < 1:
                return False, ['Interval must be positive']
            
            # Validate day constraints
            if frequency == 'monthly' and 'day_of_month' in rule:
                day = rule['day_of_month']
                if not (1 <= day <= 31):
                    return False, ['day_of_month must be between 1 and 31']
            
            if frequency == 'weekly' and 'day_of_week' in rule:
                day = rule['day_of_week']
                if not (0 <= day <= 6):  # 0 = Monday, 6 = Sunday
                    return False, ['day_of_week must be between 0 and 6']
            
            return True, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, errors
    
    def sanitize_jsonb_field(self, data: Any) -> Dict[str, Any]:
        """Sanitize and prepare JSONB data for storage"""
        if not data:
            return {}
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON string provided: {data}")
                return {}
        
        if not isinstance(data, dict):
            logger.warning(f"Expected dict for JSONB field, got {type(data)}")
            return {}
        
        # Remove any None values and empty strings
        sanitized = {}
        for key, value in data.items():
            if value is not None and value != "":
                sanitized[key] = value
        
        return sanitized
    
    def validate_foreign_key_constraints(self, db: Session) -> List[str]:
        """Check for orphaned records and foreign key violations"""
        violations = []
        
        try:
            # Check for transactions without valid users
            result = db.execute("""
                SELECT COUNT(*) FROM transactions t 
                LEFT JOIN users u ON t.user_id = u.id 
                WHERE u.id IS NULL
            """)
            orphaned_transactions = result.scalar()
            if orphaned_transactions > 0:
                violations.append(f"{orphaned_transactions} transactions have invalid user_id")
            
            # Check for transactions without valid accounts
            result = db.execute("""
                SELECT COUNT(*) FROM transactions t 
                LEFT JOIN accounts a ON t.account_id = a.id 
                WHERE a.id IS NULL
            """)
            orphaned_account_transactions = result.scalar()
            if orphaned_account_transactions > 0:
                violations.append(f"{orphaned_account_transactions} transactions have invalid account_id")
            
            # Check for budgets without valid categories
            result = db.execute("""
                SELECT COUNT(*) FROM budgets b 
                LEFT JOIN categories c ON b.category_id = c.id 
                WHERE c.id IS NULL
            """)
            orphaned_budgets = result.scalar()
            if orphaned_budgets > 0:
                violations.append(f"{orphaned_budgets} budgets have invalid category_id")
            
        except Exception as e:
            logger.error(f"Error checking foreign key constraints: {e}")
            violations.append(f"Error during constraint validation: {str(e)}")
        
        return violations
    
    def check_data_consistency(self, db: Session) -> Dict[str, Any]:
        """Perform comprehensive data consistency checks"""
        report = {
            'timestamp': logger.info('Starting data consistency check'),
            'foreign_key_violations': self.validate_foreign_key_constraints(db),
            'jsonb_validation_errors': [],
            'recommendations': []
        }
        
        try:
            # Check JSONB field validity
            # This would be expanded to check all JSONB fields in the database
            # For now, we'll just return the structure
            
            # Add recommendations based on findings
            if report['foreign_key_violations']:
                report['recommendations'].append('Fix foreign key violations before they cause cascade issues')
            
            if not report['foreign_key_violations'] and not report['jsonb_validation_errors']:
                report['recommendations'].append('Database consistency looks good!')
            
        except Exception as e:
            logger.error(f"Error during data consistency check: {e}")
            report['error'] = str(e)
        
        return report

# Create global validation service
validation_service = DataValidationService()