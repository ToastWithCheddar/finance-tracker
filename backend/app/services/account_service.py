from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.base_service import BaseService


class AccountService(BaseService[Account, AccountCreate, AccountUpdate]):
    """Account service for managing bank accounts and Plaid connections"""
    
    def __init__(self):
        super().__init__(Account)
    
    def get_by_user(self, db: Session, user_id: UUID) -> List[Account]:
        """Get all accounts for a user"""
        return db.query(Account).filter(Account.user_id == user_id).all()
    
    def get_by_user_and_id(self, db: Session, user_id: UUID, account_id: UUID) -> Optional[Account]:
        """Get account by user and account ID"""
        return db.query(Account).filter(
            Account.user_id == user_id,
            Account.id == account_id
        ).first()
    
    def get_plaid_connected(self, db: Session, user_id: UUID) -> List[Account]:
        """Get all Plaid-connected accounts for a user"""
        return db.query(Account).filter(
            Account.user_id == user_id,
            Account.plaid_account_id.isnot(None)
        ).all()
    
    def get_by_plaid_account_id(self, db: Session, plaid_account_id: str) -> Optional[Account]:
        """Get account by Plaid account ID"""
        return db.query(Account).filter(
            Account.plaid_account_id == plaid_account_id
        ).first()
    
    def create_for_user(self, db: Session, *, obj_in: AccountCreate, user_id: UUID) -> Account:
        """Create account for specific user"""
        obj_data = obj_in.model_dump()
        db_obj = Account(**obj_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_sync_status(
        self, 
        db: Session, 
        *, 
        account: Account, 
        status: str, 
        error: Optional[str] = None
    ) -> Account:
        """Update account sync status"""
        account.sync_status = status
        account.last_sync_error = error
        if status == "success":
            account.last_sync_at = db.execute("SELECT NOW()").scalar()
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    
    def update_connection_health(
        self, 
        db: Session, 
        *, 
        account: Account, 
        health_status: str
    ) -> Account:
        """Update account connection health status"""
        account.connection_health = health_status
        db.add(account)
        db.commit()
        db.refresh(account)
        return account


# Global instance
account_service = AccountService()