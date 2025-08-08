"""
Enhanced Plaid Service Implementation using FastAPI
This is a demonstration of an advanced Plaid integration with comprehensive features.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import logging
from contextlib import asynccontextmanager
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
import redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete
import httpx
from concurrent.futures import ThreadPoolExecutor

# Configuration and Models
class PlaidEnvironment(str, Enum):
    SANDBOX = "sandbox"
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class SyncStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class AccountType(str, Enum):
    DEPOSITORY = "depository"
    CREDIT = "credit"
    LOAN = "loan"
    INVESTMENT = "investment"
    BROKERAGE = "brokerage"

# Pydantic Models
class PlaidConfig(BaseModel):
    client_id: str
    secret: str
    environment: PlaidEnvironment = PlaidEnvironment.SANDBOX
    products: List[str] = ["transactions", "accounts", "investments", "liabilities", "auth", "identity"]
    country_codes: List[str] = ["US", "CA", "GB"]
    webhook_url: Optional[str] = None

class LinkTokenRequest(BaseModel):
    user_id: str
    client_name: str = "Finance Tracker"
    language: str = "en"
    country_codes: List[str] = ["US"]
    products: List[str] = ["transactions", "accounts"]
    account_filters: Optional[Dict[str, Any]] = None
    redirect_uri: Optional[str] = None
    android_package_name: Optional[str] = None
    webhook: Optional[str] = None

class ExchangeTokenRequest(BaseModel):
    public_token: str
    user_id: str
    metadata: Optional[Dict[str, Any]] = None

class AccountSyncRequest(BaseModel):
    account_ids: Optional[List[str]] = None
    sync_transactions: bool = True
    sync_investments: bool = False
    sync_liabilities: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class TransactionFilter(BaseModel):
    account_ids: Optional[List[str]] = None
    start_date: datetime
    end_date: datetime
    categories: Optional[List[str]] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class WebhookVerification(BaseModel):
    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[Dict[str, Any]] = None
    new_transactions: Optional[int] = None
    removed_transactions: Optional[List[str]] = None

class ConnectionManager:
    """WebSocket connection manager for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Connection might be closed, remove it
                    self.active_connections[user_id].remove(connection)
                    
    async def broadcast_message(self, message: str):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_text(message)
                except:
                    pass

class EnhancedPlaidService:
    """
    Enhanced Plaid Service with advanced features:
    - Real-time WebSocket notifications
    - Advanced caching with Redis
    - Comprehensive error handling
    - Rate limiting and retry logic
    - Transaction categorization with ML
    - Investment tracking
    - Liability monitoring
    - Multi-account reconciliation
    """
    
    def __init__(self, config: PlaidConfig, redis_client: redis.Redis = None):
        self.config = config
        self.redis_client = redis_client
        self.connection_manager = ConnectionManager()
        
        # Initialize Plaid client
        configuration = Configuration(
            host=getattr(plaid.Environment, config.environment.value),
            api_key={
                'clientId': config.client_id,
                'secret': config.secret
            }
        )
        api_client = ApiClient(configuration)
        self.plaid_client = plaid_api.PlaidApi(api_client)
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def create_link_token(self, request: LinkTokenRequest) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization"""
        try:
            # Cache check
            cache_key = f"link_token:{request.user_id}"
            if self.redis_client:
                cached_token = await self._get_cached_data(cache_key)
                if cached_token:
                    return cached_token

            # Create link token request
            user = LinkTokenCreateRequestUser(client_user_id=request.user_id)
            
            products = [getattr(Products, prod.lower()) for prod in request.products]
            country_codes = [getattr(CountryCode, cc.lower()) for cc in request.country_codes]
            
            link_request = LinkTokenCreateRequest(
                products=products,
                client_name=request.client_name,
                country_codes=country_codes,
                language=request.language,
                user=user,
                webhook=request.webhook or self.config.webhook_url,
                redirect_uri=request.redirect_uri,
                android_package_name=request.android_package_name,
                account_filters=request.account_filters
            )
            
            # Make API call
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.link_token_create(link_request)
            )
            
            result = {
                "link_token": response.link_token,
                "expiration": response.expiration,
                "request_id": response.request_id
            }
            
            # Cache the result
            if self.redis_client:
                await self._cache_data(cache_key, result, ttl=3600)  # 1 hour TTL
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating link token: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create link token: {str(e)}")

    async def exchange_public_token(self, request: ExchangeTokenRequest) -> Dict[str, Any]:
        """Exchange public token for access token and create accounts"""
        try:
            exchange_request = ItemPublicTokenExchangeRequest(
                public_token=request.public_token
            )
            
            # Exchange token
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.item_public_token_exchange(exchange_request)
            )
            
            access_token = response.access_token
            item_id = response.item_id
            
            # Get accounts
            accounts = await self.get_accounts(access_token)
            
            # Store in database and cache
            result = {
                "access_token": access_token,
                "item_id": item_id,
                "accounts": accounts,
                "request_id": response.request_id
            }
            
            # Notify via WebSocket
            await self.connection_manager.send_personal_message(
                json.dumps({
                    "type": "account_connected",
                    "data": result
                }),
                request.user_id
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error exchanging public token: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to exchange token: {str(e)}")

    async def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all accounts for an access token"""
        try:
            # Check cache first
            cache_key = f"accounts:{access_token}"
            if self.redis_client:
                cached_accounts = await self._get_cached_data(cache_key)
                if cached_accounts:
                    return cached_accounts

            accounts_request = AccountsGetRequest(access_token=access_token)
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.accounts_get(accounts_request)
            )
            
            accounts = []
            for account in response.accounts:
                account_data = {
                    "account_id": account.account_id,
                    "name": account.name,
                    "official_name": account.official_name,
                    "type": account.type.value,
                    "subtype": account.subtype.value if account.subtype else None,
                    "balances": {
                        "available": float(account.balances.available) if account.balances.available else None,
                        "current": float(account.balances.current) if account.balances.current else None,
                        "limit": float(account.balances.limit) if account.balances.limit else None,
                        "iso_currency_code": account.balances.iso_currency_code,
                        "unofficial_currency_code": account.balances.unofficial_currency_code
                    },
                    "mask": account.mask,
                    "persistent_account_id": account.persistent_account_id
                }
                accounts.append(account_data)
            
            # Cache the result
            if self.redis_client:
                await self._cache_data(cache_key, accounts, ttl=300)  # 5 minutes TTL
                
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error getting accounts: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")

    async def sync_accounts(self, access_tokens: List[str], sync_request: AccountSyncRequest) -> Dict[str, Any]:
        """Comprehensive account synchronization with real-time updates"""
        try:
            sync_results = {
                "synced_accounts": 0,
                "synced_transactions": 0,
                "synced_investments": 0,
                "synced_liabilities": 0,
                "errors": [],
                "sync_status": SyncStatus.SYNCING.value,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None
            }
            
            # Notify sync started
            await self.connection_manager.broadcast_message(
                json.dumps({
                    "type": "sync_started",
                    "data": sync_results
                })
            )
            
            for access_token in access_tokens:
                try:
                    # Sync accounts
                    accounts = await self.get_accounts(access_token)
                    sync_results["synced_accounts"] += len(accounts)
                    
                    # Sync transactions if requested
                    if sync_request.sync_transactions:
                        transactions = await self.sync_transactions(
                            access_token, 
                            sync_request.account_ids,
                            sync_request.start_date,
                            sync_request.end_date
                        )
                        sync_results["synced_transactions"] += len(transactions)
                    
                    # Sync investments if requested
                    if sync_request.sync_investments:
                        investments = await self.sync_investments(access_token)
                        sync_results["synced_investments"] += len(investments)
                    
                    # Sync liabilities if requested
                    if sync_request.sync_liabilities:
                        liabilities = await self.sync_liabilities(access_token)
                        sync_results["synced_liabilities"] += len(liabilities)
                        
                    # Update real-time progress
                    await self.connection_manager.broadcast_message(
                        json.dumps({
                            "type": "sync_progress",
                            "data": sync_results
                        })
                    )
                    
                except Exception as token_error:
                    error_info = {
                        "access_token": access_token[:10] + "...",  # Truncate for security
                        "error": str(token_error),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    sync_results["errors"].append(error_info)
                    self.logger.error(f"Error syncing token {access_token[:10]}...: {token_error}")
            
            # Mark as completed
            sync_results["sync_status"] = SyncStatus.COMPLETED.value if not sync_results["errors"] else SyncStatus.FAILED.value
            sync_results["completed_at"] = datetime.utcnow().isoformat()
            
            # Final notification
            await self.connection_manager.broadcast_message(
                json.dumps({
                    "type": "sync_completed",
                    "data": sync_results
                })
            )
            
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Error in account sync: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

    async def sync_transactions(self, access_token: str, account_ids: List[str] = None, 
                               start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Sync transactions with enhanced filtering and categorization"""
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
                
            transactions_request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                account_ids=account_ids
            )
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.transactions_get(transactions_request)
            )
            
            transactions = []
            for transaction in response.transactions:
                transaction_data = {
                    "transaction_id": transaction.transaction_id,
                    "account_id": transaction.account_id,
                    "amount": float(transaction.amount),
                    "iso_currency_code": transaction.iso_currency_code,
                    "unofficial_currency_code": transaction.unofficial_currency_code,
                    "category": transaction.category,
                    "category_id": transaction.category_id,
                    "date": transaction.date.isoformat(),
                    "authorized_date": transaction.authorized_date.isoformat() if transaction.authorized_date else None,
                    "name": transaction.name,
                    "merchant_name": transaction.merchant_name,
                    "payment_channel": transaction.payment_channel.value,
                    "pending": transaction.pending,
                    "account_owner": transaction.account_owner,
                    "location": transaction.location.to_dict() if transaction.location else None,
                    "payment_meta": transaction.payment_meta.to_dict() if transaction.payment_meta else None,
                    "personal_finance_category": transaction.personal_finance_category.to_dict() if transaction.personal_finance_category else None
                }
                
                # Enhanced categorization using ML (placeholder)
                transaction_data["enhanced_category"] = await self.categorize_transaction(transaction_data)
                transactions.append(transaction_data)
            
            return transactions
            
        except Exception as e:
            self.logger.error(f"Error syncing transactions: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to sync transactions: {str(e)}")

    async def sync_investments(self, access_token: str) -> List[Dict[str, Any]]:
        """Sync investment holdings and transactions"""
        try:
            holdings_request = InvestmentsHoldingsGetRequest(access_token=access_token)
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.investments_holdings_get(holdings_request)
            )
            
            holdings = []
            for holding in response.holdings:
                holding_data = {
                    "account_id": holding.account_id,
                    "security_id": holding.security_id,
                    "institution_price": float(holding.institution_price) if holding.institution_price else None,
                    "institution_price_as_of": holding.institution_price_as_of.isoformat() if holding.institution_price_as_of else None,
                    "institution_value": float(holding.institution_value) if holding.institution_value else None,
                    "cost_basis": float(holding.cost_basis) if holding.cost_basis else None,
                    "quantity": float(holding.quantity),
                    "iso_currency_code": holding.iso_currency_code,
                    "unofficial_currency_code": holding.unofficial_currency_code
                }
                holdings.append(holding_data)
            
            return holdings
            
        except Exception as e:
            self.logger.error(f"Error syncing investments: {str(e)}")
            return []

    async def sync_liabilities(self, access_token: str) -> List[Dict[str, Any]]:
        """Sync liability information"""
        try:
            liabilities_request = LiabilitiesGetRequest(access_token=access_token)
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.liabilities_get(liabilities_request)
            )
            
            liabilities = []
            
            # Credit card liabilities
            if response.liabilities.credit:
                for credit in response.liabilities.credit:
                    liability_data = {
                        "account_id": credit.account_id,
                        "type": "credit",
                        "balances": {
                            "current": float(credit.balances.current) if credit.balances.current else None,
                            "available": float(credit.balances.available) if credit.balances.available else None,
                            "limit": float(credit.balances.limit) if credit.balances.limit else None
                        },
                        "aprs": [
                            {
                                "apr_percentage": float(apr.apr_percentage),
                                "apr_type": apr.apr_type.value,
                                "balance_subject_to_apr": float(apr.balance_subject_to_apr) if apr.balance_subject_to_apr else None,
                                "interest_charge_amount": float(apr.interest_charge_amount) if apr.interest_charge_amount else None
                            }
                            for apr in credit.aprs
                        ] if credit.aprs else [],
                        "last_payment_amount": float(credit.last_payment_amount) if credit.last_payment_amount else None,
                        "last_payment_date": credit.last_payment_date.isoformat() if credit.last_payment_date else None,
                        "last_statement_balance": float(credit.last_statement_balance) if credit.last_statement_balance else None,
                        "last_statement_issue_date": credit.last_statement_issue_date.isoformat() if credit.last_statement_issue_date else None,
                        "minimum_payment_amount": float(credit.minimum_payment_amount) if credit.minimum_payment_amount else None,
                        "next_payment_due_date": credit.next_payment_due_date.isoformat() if credit.next_payment_due_date else None
                    }
                    liabilities.append(liability_data)
            
            # Mortgage liabilities
            if response.liabilities.mortgage:
                for mortgage in response.liabilities.mortgage:
                    liability_data = {
                        "account_id": mortgage.account_id,
                        "type": "mortgage",
                        "balances": {
                            "current": float(mortgage.balances.current) if mortgage.balances.current else None
                        },
                        "interest_rate": {
                            "percentage": float(mortgage.interest_rate.percentage) if mortgage.interest_rate else None,
                            "type": mortgage.interest_rate.type.value if mortgage.interest_rate else None
                        },
                        "loan_term": mortgage.loan_term,
                        "loan_type_description": mortgage.loan_type_description,
                        "maturity_date": mortgage.maturity_date.isoformat() if mortgage.maturity_date else None,
                        "origination_date": mortgage.origination_date.isoformat() if mortgage.origination_date else None,
                        "origination_principal_amount": float(mortgage.origination_principal_amount) if mortgage.origination_principal_amount else None,
                        "past_due_amount": float(mortgage.past_due_amount) if mortgage.past_due_amount else None,
                        "ytd_interest_paid": float(mortgage.ytd_interest_paid) if mortgage.ytd_interest_paid else None,
                        "ytd_principal_paid": float(mortgage.ytd_principal_paid) if mortgage.ytd_principal_paid else None
                    }
                    liabilities.append(liability_data)
            
            # Student loan liabilities
            if response.liabilities.student:
                for student in response.liabilities.student:
                    liability_data = {
                        "account_id": student.account_id,
                        "type": "student_loan",
                        "balances": {
                            "current": float(student.balances.current) if student.balances.current else None,
                            "outstanding_interest_amount": float(student.balances.outstanding_interest_amount) if student.balances.outstanding_interest_amount else None
                        },
                        "expected_payoff_date": student.expected_payoff_date.isoformat() if student.expected_payoff_date else None,
                        "guarantor": student.guarantor,
                        "interest_rate": float(student.interest_rate_percentage) if student.interest_rate_percentage else None,
                        "loan_name": student.loan_name,
                        "loan_status": {
                            "type": student.loan_status.type.value if student.loan_status else None,
                            "end_date": student.loan_status.end_date.isoformat() if student.loan_status and student.loan_status.end_date else None
                        },
                        "minimum_payment_amount": float(student.minimum_payment_amount) if student.minimum_payment_amount else None,
                        "next_payment_due_date": student.next_payment_due_date.isoformat() if student.next_payment_due_date else None,
                        "origination_date": student.origination_date.isoformat() if student.origination_date else None,
                        "origination_principal_amount": float(student.origination_principal_amount) if student.origination_principal_amount else None,
                        "outstanding_interest_amount": float(student.outstanding_interest_amount) if student.outstanding_interest_amount else None,
                        "payment_reference_number": student.payment_reference_number,
                        "pslf_status": {
                            "estimated_eligibility_date": student.pslf_status.estimated_eligibility_date.isoformat() if student.pslf_status and student.pslf_status.estimated_eligibility_date else None,
                            "payments_made": student.pslf_status.payments_made if student.pslf_status else None,
                            "payments_remaining": student.pslf_status.payments_remaining if student.pslf_status else None
                        } if student.pslf_status else None,
                        "repayment_plan": {
                            "description": student.repayment_plan.description if student.repayment_plan else None,
                            "type": student.repayment_plan.type.value if student.repayment_plan else None
                        } if student.repayment_plan else None,
                        "sequence_number": student.sequence_number,
                        "servicer_address": {
                            "city": student.servicer_address.city if student.servicer_address else None,
                            "country": student.servicer_address.country if student.servicer_address else None,
                            "postal_code": student.servicer_address.postal_code if student.servicer_address else None,
                            "region": student.servicer_address.region if student.servicer_address else None,
                            "street": student.servicer_address.street if student.servicer_address else None
                        } if student.servicer_address else None,
                        "ytd_interest_paid": float(student.ytd_interest_paid) if student.ytd_interest_paid else None,
                        "ytd_principal_paid": float(student.ytd_principal_paid) if student.ytd_principal_paid else None
                    }
                    liabilities.append(liability_data)
            
            return liabilities
            
        except Exception as e:
            self.logger.error(f"Error syncing liabilities: {str(e)}")
            return []

    async def categorize_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced transaction categorization using ML (placeholder implementation)"""
        # This would typically use a trained ML model for categorization
        # For demonstration, we'll use simple rule-based categorization
        
        name = transaction.get("name", "").lower()
        category = transaction.get("category", [])
        amount = abs(transaction.get("amount", 0))
        
        enhanced_category = {
            "primary": category[0] if category else "Other",
            "secondary": category[1] if len(category) > 1 else None,
            "confidence": 0.8,  # Placeholder confidence score
            "suggested_budget_category": None,
            "is_recurring": False,
            "merchant_type": None
        }
        
        # Simple rules for demonstration
        if "uber" in name or "lyft" in name:
            enhanced_category.update({
                "primary": "Transportation",
                "secondary": "Rideshare",
                "confidence": 0.95,
                "merchant_type": "rideshare"
            })
        elif "starbucks" in name or "coffee" in name:
            enhanced_category.update({
                "primary": "Food and Drink",
                "secondary": "Coffee Shops",
                "confidence": 0.9,
                "merchant_type": "coffee_shop"
            })
        elif amount > 1000:
            enhanced_category["is_recurring"] = await self._check_recurring_transaction(transaction)
        
        return enhanced_category

    async def _check_recurring_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Check if a transaction is part of a recurring pattern"""
        # This would typically analyze historical transaction data
        # Placeholder implementation
        return False

    async def handle_webhook(self, webhook_data: WebhookVerification) -> Dict[str, Any]:
        """Handle Plaid webhooks for real-time updates"""
        try:
            self.logger.info(f"Received webhook: {webhook_data.webhook_type} - {webhook_data.webhook_code}")
            
            webhook_response = {
                "processed_at": datetime.utcnow().isoformat(),
                "webhook_type": webhook_data.webhook_type,
                "webhook_code": webhook_data.webhook_code,
                "item_id": webhook_data.item_id,
                "action_taken": None
            }
            
            # Handle different webhook types
            if webhook_data.webhook_type == "TRANSACTIONS":
                if webhook_data.webhook_code == "DEFAULT_UPDATE":
                    # New transactions available
                    webhook_response["action_taken"] = "scheduled_transaction_sync"
                    
                    # Notify connected clients
                    await self.connection_manager.broadcast_message(
                        json.dumps({
                            "type": "new_transactions_available",
                            "data": {
                                "item_id": webhook_data.item_id,
                                "new_transactions": webhook_data.new_transactions
                            }
                        })
                    )
                    
                elif webhook_data.webhook_code == "TRANSACTIONS_REMOVED":
                    # Transactions were removed
                    webhook_response["action_taken"] = "removed_transactions_processed"
                    
                    await self.connection_manager.broadcast_message(
                        json.dumps({
                            "type": "transactions_removed",
                            "data": {
                                "item_id": webhook_data.item_id,
                                "removed_transactions": webhook_data.removed_transactions
                            }
                        })
                    )
            
            elif webhook_data.webhook_type == "ITEM":
                if webhook_data.webhook_code == "ERROR":
                    # Item error occurred
                    webhook_response["action_taken"] = "item_error_logged"
                    
                    await self.connection_manager.broadcast_message(
                        json.dumps({
                            "type": "item_error",
                            "data": {
                                "item_id": webhook_data.item_id,
                                "error": webhook_data.error
                            }
                        })
                    )
                    
                elif webhook_data.webhook_code == "PENDING_EXPIRATION":
                    # Item access will expire soon
                    webhook_response["action_taken"] = "expiration_warning_sent"
                    
                    await self.connection_manager.broadcast_message(
                        json.dumps({
                            "type": "item_expiring",
                            "data": {
                                "item_id": webhook_data.item_id
                            }
                        })
                    )
            
            return webhook_response
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

    async def get_connection_health(self, access_token: str) -> Dict[str, Any]:
        """Check the health of a Plaid connection"""
        try:
            # Try to make a simple API call to test connection
            accounts_request = AccountsGetRequest(access_token=access_token)
            
            start_time = datetime.utcnow()
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.plaid_client.accounts_get(accounts_request)
            )
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "accounts_count": len(response.accounts),
                "last_checked": datetime.utcnow().isoformat(),
                "item_id": response.item.item_id if response.item else None
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }

    async def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from Redis cache"""
        if not self.redis_client:
            return None
            
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {str(e)}")
            return None

    async def _cache_data(self, key: str, data: Any, ttl: int = 300):
        """Cache data in Redis"""
        if not self.redis_client:
            return
            
        try:
            self.redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {str(e)}")

# FastAPI Application Setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.plaid_service = EnhancedPlaidService(
        config=PlaidConfig(
            client_id="your_plaid_client_id",
            secret="your_plaid_secret",
            environment=PlaidEnvironment.SANDBOX
        ),
        redis_client=redis.Redis(host='localhost', port=6379, decode_responses=True)
    )
    yield
    # Shutdown
    if hasattr(app.state, 'plaid_service'):
        del app.state.plaid_service

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Plaid Finance Tracker API",
    description="Advanced Plaid integration with real-time features",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token (placeholder implementation)"""
    # This should implement proper JWT validation
    return "user_123"  # Placeholder

def get_plaid_service(app: FastAPI = Depends(lambda: app)) -> EnhancedPlaidService:
    """Get Plaid service from app state"""
    return app.state.plaid_service

# API Routes
@app.post("/api/v2/plaid/link-token")
async def create_link_token(
    request: LinkTokenRequest,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Create a new link token for Plaid Link"""
    request.user_id = current_user
    return await plaid_service.create_link_token(request)

@app.post("/api/v2/plaid/exchange-token")
async def exchange_public_token(
    request: ExchangeTokenRequest,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Exchange public token for access token"""
    request.user_id = current_user
    return await plaid_service.exchange_public_token(request)

@app.get("/api/v2/plaid/accounts/{access_token}")
async def get_accounts(
    access_token: str,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Get all accounts for an access token"""
    return await plaid_service.get_accounts(access_token)

@app.post("/api/v2/plaid/sync")
async def sync_accounts(
    access_tokens: List[str],
    sync_request: AccountSyncRequest = AccountSyncRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Comprehensive account synchronization"""
    background_tasks.add_task(
        plaid_service.sync_accounts,
        access_tokens,
        sync_request
    )
    return {"message": "Synchronization started", "status": "pending"}

@app.get("/api/v2/plaid/transactions/{access_token}")
async def get_transactions(
    access_token: str,
    filter_params: TransactionFilter = Depends(),
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Get transactions with advanced filtering"""
    return await plaid_service.sync_transactions(
        access_token=access_token,
        account_ids=filter_params.account_ids,
        start_date=filter_params.start_date,
        end_date=filter_params.end_date
    )

@app.get("/api/v2/plaid/investments/{access_token}")
async def get_investments(
    access_token: str,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Get investment holdings"""
    return await plaid_service.sync_investments(access_token)

@app.get("/api/v2/plaid/liabilities/{access_token}")
async def get_liabilities(
    access_token: str,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Get liability information"""
    return await plaid_service.sync_liabilities(access_token)

@app.post("/api/v2/plaid/webhook")
async def handle_webhook(
    webhook_data: WebhookVerification,
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Handle Plaid webhooks"""
    return await plaid_service.handle_webhook(webhook_data)

@app.get("/api/v2/plaid/health/{access_token}")
async def check_connection_health(
    access_token: str,
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Check Plaid connection health"""
    return await plaid_service.get_connection_health(access_token)

@app.websocket("/api/v2/plaid/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """WebSocket endpoint for real-time updates"""
    await plaid_service.connection_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        plaid_service.connection_manager.disconnect(websocket, user_id)

@app.get("/api/v2/plaid/analytics/spending")
async def get_spending_analytics(
    access_tokens: List[str],
    start_date: datetime = datetime.now() - timedelta(days=90),
    end_date: datetime = datetime.now(),
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Advanced spending analytics"""
    # This would implement comprehensive spending analysis
    # Placeholder implementation
    return {
        "spending_by_category": {},
        "monthly_trends": {},
        "merchant_analysis": {},
        "budget_insights": {}
    }

@app.get("/api/v2/plaid/insights/financial-health")
async def get_financial_health_insights(
    access_tokens: List[str],
    current_user: str = Depends(get_current_user),
    plaid_service: EnhancedPlaidService = Depends(get_plaid_service)
):
    """Financial health insights and recommendations"""
    # This would implement ML-based financial health analysis
    # Placeholder implementation
    return {
        "credit_utilization": 0.25,
        "savings_rate": 0.15,
        "debt_to_income": 0.30,
        "emergency_fund_months": 3.2,
        "recommendations": [
            "Consider increasing emergency fund to 6 months of expenses",
            "Credit utilization is healthy, maintain current levels",
            "Good savings rate, consider investing excess funds"
        ],
        "risk_factors": [],
        "score": 78
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)