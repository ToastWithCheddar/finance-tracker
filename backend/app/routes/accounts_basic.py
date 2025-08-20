"""
Basic account management API endpoints.
Handles core CRUD operations for user accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.dependencies import get_account_service, get_owned_account
from app.models.user import User
from app.schemas.account import (
    Account as AccountSchema, 
    AccountCreate, 
    AccountUpdate,
    AccountWithTransactions
)
from app.services.account_service import AccountService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[AccountSchema])
async def get_user_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """Get all accounts for the current user"""
    accounts = account_service.get_by_user(db=db, user_id=current_user.id)
    return accounts


@router.post("/", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """Create a new account manually"""
    account = account_service.create(
        db=db, 
        obj_in=account_data, 
        user_id=current_user.id
    )
    return account


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account = Depends(get_owned_account)
):
    """Get a specific account by ID"""
    return account


@router.put("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_update: AccountUpdate,
    account = Depends(get_owned_account),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """Update an existing account"""
    updated_account = account_service.update(db=db, db_obj=account, obj_in=account_update)
    return updated_account


@router.delete("/{account_id}")
async def delete_account(
    account = Depends(get_owned_account),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """Delete an account"""
    account_service.remove(db=db, id=account.id)
    return {"message": "Account deleted successfully"}


@router.get("/{account_id}/with-transactions", response_model=AccountWithTransactions)
async def get_account_with_transactions(
    account = Depends(get_owned_account),
    db: Session = Depends(get_db_with_user_context),
    account_service: AccountService = Depends(get_account_service)
):
    """Get account with its transactions"""
    account_with_transactions = account_service.get_with_transactions(
        db=db, 
        account_id=account.id
    )
    return account_with_transactions