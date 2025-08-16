"""
Enhanced Plaid Integration Service with Sandbox Support and Real-time Sync
Comprehensive implementation for Plaid bank account connections
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import requests
import json
import time
import asyncio
import hashlib
from dataclasses import dataclass
from uuid import UUID

from app.config import settings
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.transaction import TransactionCreate
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

@dataclass
class PlaidAccountSync:
    """Data class for account sync status"""
    account_id: str
    status: str  # syncing, synced, error
    last_sync: Optional[datetime]
    error_message: Optional[str] = None
    transactions_synced: int = 0
    balance_updated: bool = False

class EnhancedPlaidService:
    """Enhanced Plaid service with comprehensive sandbox integration"""
    
    def __init__(self):
        self.enabled = settings.ENABLE_PLAID
        self.client_id = settings.PLAID_CLIENT_ID
        self.secret = settings.PLAID_SECRET
        self.environment = settings.PLAID_ENV
        self.products = settings.PLAID_PRODUCTS.split(",") if settings.PLAID_PRODUCTS else []
        self.country_codes = settings.PLAID_COUNTRY_CODES.split(",") if settings.PLAID_COUNTRY_CODES else []
        
        if not self.enabled:
            logger.info("Plaid integration is disabled")
            return
            
        # Validate configuration
        if self.client_id == "your_plaid_client_id" or self.secret == "your_plaid_secret":
            logger.warning("Plaid credentials are not configured. Using sandbox test credentials.")
            # For development, you can use test credentials here
        
        # Plaid API endpoints
        self.base_url = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }.get(self.environment, 'https://sandbox.plaid.com')
        
        self.account_service = AccountService()
        self.transaction_service = TransactionService()
        
        # Sync tracking
        self.active_syncs: Dict[str, PlaidAccountSync] = {}
        
        logger.info(f"Enhanced Plaid service initialized for {self.environment} environment")
        logger.debug(f"Plaid client_id: {self.client_id[:10]}... (truncated)")
        logger.debug(f"Plaid secret: {'*' * len(self.secret) if self.secret else 'EMPTY'}")
    
    async def create_link_token(self, user_id: str, update_mode: bool = False) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization or update"""
        if not self.enabled:
            return self._disabled_response()
        
        try:
            link_token_request = {
                'user': {
                    'client_user_id': str(user_id)
                },
                'client_name': 'Finance Tracker',
                'products': ['transactions'],
                'additional_consented_products': ['liabilities'],
                'country_codes': ['US'],
                'language': 'en'
            }
            
            # Add update mode if re-linking
            if update_mode:
                link_token_request['update'] = {
                    'account_selection_enabled': True
                }
            
            # Remove sandbox override for now
            
            result = await self._make_request('link/token/create', link_token_request)
            
            return {
                'success': True,
                'link_token': result.get('link_token'),
                'expiration': result.get('expiration'),
                'request_id': result.get('request_id'),
                'environment': self.environment
            }
            
        except Exception as e:
            logger.error(f"Failed to create link token: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create link token'
            }
    
    async def exchange_public_token(self, public_token: str, user_id: str, db: Session) -> Dict[str, Any]:
        """Exchange public token for access token and create accounts"""
        if not self.enabled:
            return self._disabled_response()
        
        try:
            logger.info(f"Starting token exchange for user: {user_id}")
            
            # Exchange token
            exchange_request = {
                'public_token': public_token
            }
            
            result = await self._make_request('item/public_token/exchange', exchange_request)
            access_token = result.get('access_token')
            item_id = result.get('item_id')
            
            if not access_token:
                raise Exception("No access token received from Plaid")
            
            logger.info(f"Successfully exchanged token, got access_token and item_id: {item_id}")
            
            # Get accounts and institution info
            accounts_info = await self.fetch_accounts_and_institution(access_token)
            logger.info(f"Fetched {len(accounts_info.get('accounts', []))} accounts from Plaid")
            
            # Create accounts in database with proper transaction management
            created_accounts = []
            institution_info = accounts_info.get('institution')
            
            try:
                # Process each account within a database transaction
                for account_data in accounts_info.get('accounts', []):
                    logger.info(f"Processing account: {account_data.get('account_id', 'unknown')}")
                    account = await self._create_or_update_account(
                        account_data, access_token, item_id, user_id, db, institution_info
                    )
                    created_accounts.append(account)
                    logger.info(f"Successfully processed account: {account.name} (ID: {account.id})")
                
                # Commit the transaction after all accounts are created
                db.commit()
                logger.info(f"Successfully committed {len(created_accounts)} accounts to database")
                
                # Initial sync of recent transactions
                try:
                    await self._initial_transaction_sync(created_accounts, access_token, db)
                    logger.info("Initial transaction sync completed")
                except Exception as sync_error:
                    logger.warning(f"Initial transaction sync failed, but accounts created: {sync_error}")
                    # Don't fail the whole process if transaction sync fails
                
            except Exception as db_error:
                logger.error(f"Database error during account creation: {db_error}")
                db.rollback()
                raise Exception(f"Failed to create accounts in database: {str(db_error)}")
            
            return {
                'success': True,
                'access_token': access_token,
                'item_id': item_id,
                'accounts': created_accounts,
                'institution': accounts_info.get('institution'),
                'accounts_created': len(created_accounts),
                'message': f"Successfully connected {len(created_accounts)} accounts"
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}", exc_info=True)
            # Ensure database rollback on any error
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback database transaction: {rollback_error}")
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to connect bank account. Please try again.',
                'accounts': []
            }
    
    async def fetch_accounts_and_institution(self, access_token: str) -> Dict[str, Any]:
        """Fetch comprehensive account and institution information"""
        try:
            # Get accounts
            accounts_result = await self._make_request('accounts/get', {
                'access_token': access_token
            })
            
            # Get item and institution info
            item_result = await self._make_request('item/get', {
                'access_token': access_token
            })
            
            institution_info = None
            item = item_result.get('item', {})
            institution_id = item.get('institution_id')
            
            if institution_id:
                institution_result = await self._make_request('institutions/get_by_id', {
                    'institution_id': institution_id,
                    'country_codes': self.country_codes
                })
                institution_info = institution_result.get('institution')
            
            return {
                'accounts': accounts_result.get('accounts', []),
                'item': item,
                'institution': institution_info
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch accounts and institution: {e}")
            raise
    
    async def _create_or_update_account(
        self, 
        plaid_account: Dict[str, Any], 
        access_token: str, 
        item_id: str, 
        user_id: str, 
        db: Session,
        institution_info: Optional[Dict[str, Any]] = None
    ) -> Account:
        """Create new account or update existing one from Plaid data"""
        
        plaid_account_id = plaid_account.get('account_id')
        
        # Check if account already exists
        existing_account = db.query(Account).filter(
            Account.plaid_account_id == plaid_account_id
        ).first()
        
        if existing_account:
            # Update existing account
            return await self._update_existing_account(existing_account, plaid_account, access_token, item_id, db, institution_info)
        else:
            # Create new account
            return await self._create_new_account(plaid_account, access_token, item_id, user_id, db, institution_info)
    
    async def _create_new_account(
        self, 
        plaid_account: Dict[str, Any], 
        access_token: str, 
        item_id: str, 
        user_id: str, 
        db: Session,
        institution_info: Optional[Dict[str, Any]] = None
    ) -> Account:
        """Create a new account from Plaid data"""
        
        # Debug logging to track user_id parameter
        logger.info(f"Creating account - User ID parameter: {user_id}")
        logger.info(f"Creating account - User ID type: {type(user_id)}")
        logger.info(f"Creating account - Plaid account ID: {plaid_account.get('account_id')}")
        
        # Early validation - prevent None user_id
        if not user_id or user_id in ('None', 'null', ''):
            logger.error(f"Invalid user_id received: {user_id} (type: {type(user_id)})")
            raise Exception(f"Invalid user_id: {user_id}. User authentication failed.")
        
        # Convert string user_id to UUID
        try:
            user_uuid = UUID(str(user_id))
            logger.info(f"Converted user_id to UUID: {user_uuid}")
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert user_id to UUID: {user_id} - {e}")
            raise Exception(f"Invalid user_id format: {user_id}")
        
        
        # Map Plaid account types
        account_type = self._map_account_type(plaid_account)
        
        # Get balances
        balances = plaid_account.get('balances', {})
        current_balance = balances.get('current', 0) or 0
        available_balance = balances.get('available') or current_balance
        
        # Create metadata
        metadata = {
            'plaid_type': plaid_account.get('type'),
            'plaid_subtype': plaid_account.get('subtype'),
            'mask': plaid_account.get('mask'),
            'official_name': plaid_account.get('official_name'),
            'available_balance': available_balance,
            'iso_currency_code': balances.get('iso_currency_code', 'USD'),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'sync_history': []
        }
        
        # Add institution information if available
        if institution_info:
            metadata.update({
                'institution_name': institution_info.get('name'),
                'institution_id': institution_info.get('institution_id'),
                'institution_url': institution_info.get('url'),
                'institution_logo': institution_info.get('logo'),
                'institution_primary_color': institution_info.get('primary_color')
            })
        
        # Validate required fields before creating account
        account_name = plaid_account.get('official_name') or plaid_account.get('name', 'Unknown Account')
        plaid_account_id = plaid_account.get('account_id')
        
        if not plaid_account_id:
            raise Exception(f"Missing required plaid_account_id for account: {account_name}")
        
        if not access_token:
            raise Exception(f"Missing access_token for account: {account_name}")
        
        # Application-level deduplication guard: if an account exists for this user with the
        # same item and characteristics, update it instead of creating a new one
        try:
            potential_duplicate = db.query(Account).filter(
                Account.user_id == user_uuid,
                (
                    (Account.plaid_account_id == plaid_account_id) |
                    (
                        (Account.plaid_item_id == item_id) &
                        (Account.name == account_name) &
                        (Account.account_type == account_type)
                    )
                )
            ).first()
        except Exception:
            potential_duplicate = None
        
        if potential_duplicate:
            logger.info(
                f"Found potential duplicate account for user {user_uuid}: {potential_duplicate.id}. Updating instead of creating."
            )
            # Ensure Plaid identifiers are up to date
            potential_duplicate.plaid_account_id = plaid_account_id
            potential_duplicate.plaid_item_id = item_id
            potential_duplicate.plaid_access_token = access_token
            db.add(potential_duplicate)
            db.commit()
            db.refresh(potential_duplicate)
            # Continue with regular update path to refresh balances/metadata
            return await self._update_existing_account(
                potential_duplicate, plaid_account, access_token, item_id, db, institution_info
            )

        # Debug logging before AccountCreate
        logger.info(f"Creating AccountCreate object - User UUID: {user_uuid}, Account: {account_name}, Plaid ID: {plaid_account_id}")
        
        try:
            account_create = AccountCreate(
                user_id=user_uuid,
                name=account_name,
                account_type=account_type,
                balance_cents=int(current_balance * 100),
                currency=balances.get('iso_currency_code', 'USD'),
                is_active=True,
                plaid_account_id=plaid_account_id,
                plaid_access_token=access_token,
                plaid_item_id=item_id,
                account_metadata=metadata,
                sync_status='synced',
                connection_health='healthy',
                sync_frequency='daily',
                last_sync_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"AccountCreate object created successfully for {account_name}")
            
            # Create account with enhanced error handling
            account = self.account_service.create(db=db, obj_in=account_create)
            
            # Verify account was created properly
            if not account or not account.id:
                raise Exception(f"Account creation failed - no account ID returned for {account_name}")
            
            logger.info(f"✅ Successfully created Plaid account: {account.name} (ID: {account.id}, Plaid ID: {account.plaid_account_id})")
            
            return account
            
        except Exception as create_error:
            logger.error(f"❌ Failed to create account {account_name}: {create_error}", exc_info=True)
            raise Exception(f"Account creation failed for {account_name}: {str(create_error)}")
    
    async def _update_existing_account(
        self, 
        account: Account, 
        plaid_account: Dict[str, Any], 
        access_token: str, 
        item_id: Optional[str], 
        db: Session,
        institution_info: Optional[Dict[str, Any]] = None
    ) -> Account:
        """Update existing account with fresh Plaid data"""
        
        balances = plaid_account.get('balances', {})
        new_balance = balances.get('current', 0) or 0
        
        # Update account
        account.balance_cents = int(new_balance * 100)
        account.plaid_access_token = access_token
        if item_id:
            account.plaid_item_id = item_id
        account.sync_status = 'synced'
        account.connection_health = 'healthy'
        account.last_sync_at = datetime.now(timezone.utc)
        
        # Update metadata
        metadata = account.account_metadata or {}
        metadata.update({
            'available_balance': balances.get('available', new_balance),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'previous_balance': account.balance_cents / 100 if account.balance_cents else 0
        })
        
        # Add institution information if available
        if institution_info:
            metadata.update({
                'institution_name': institution_info.get('name'),
                'institution_id': institution_info.get('institution_id'),
                'institution_url': institution_info.get('url'),
                'institution_logo': institution_info.get('logo'),
                'institution_primary_color': institution_info.get('primary_color')
            })
        
        # Add to sync history
        sync_history = metadata.get('sync_history', [])
        sync_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'balance': new_balance,
            'status': 'success'
        })
        
        # Keep only last 10 sync records
        metadata['sync_history'] = sync_history[-10:]
        account.account_metadata = metadata
        
        db.add(account)
        db.commit()
        
        logger.info(f"Updated Plaid account: {account.name} ({account.id})")
        return account
    
    def _map_account_type(self, plaid_account: Dict[str, Any]) -> str:
        """Map Plaid account type to our account types"""
        
        type_mapping = {
            'depository': {
                'checking': 'checking',
                'savings': 'savings',
                'cd': 'savings',
                'money market': 'savings',
                'paypal': 'checking',
                'prepaid': 'checking'
            },
            'credit': {
                'credit card': 'credit_card',
                'paypal': 'credit_card'
            },
            'loan': {
                'auto': 'loan',
                'business': 'loan',
                'commercial': 'loan',
                'construction': 'loan',
                'consumer': 'loan',
                'home equity': 'loan',
                'loan': 'loan',
                'mortgage': 'mortgage',
                'overdraft': 'loan',
                'line of credit': 'loan',
                'student': 'loan'
            },
            'investment': {
                'brokerage': 'investment',
                '401a': 'retirement',
                '401k': 'retirement',
                '403B': 'retirement',
                '457b': 'retirement',
                '529': 'investment',
                'ira': 'retirement',
                'roth': 'retirement',
                'sep': 'retirement',
                'simple ira': 'retirement',
                'sarsep': 'retirement',
                'ugma': 'investment',
                'utma': 'investment'
            },
            'other': {
                'other': 'other'
            }
        }
        
        plaid_type = plaid_account.get('type', '').lower()
        plaid_subtype = plaid_account.get('subtype', '').lower()
        
        if plaid_type in type_mapping:
            subtype_mapping = type_mapping[plaid_type]
            if plaid_subtype in subtype_mapping:
                return subtype_mapping[plaid_subtype]
            else:
                # Return first available type for this category
                return list(subtype_mapping.values())[0]
        
        return 'checking'  # Safe default
    
    async def sync_account_balances(
        self, 
        db: Session, 
        account_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """Enhanced account balance synchronization with real-time updates"""
        if not self.enabled:
            return self._disabled_response()
        
        results = {
            'synced': [],
            'failed': [],
            'skipped': [],
            'total_accounts': 0,
            'sync_time': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Get accounts to sync
            query = db.query(Account).filter(Account.plaid_access_token.isnot(None))
            
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            if user_id:
                query = query.filter(Account.user_id == user_id)
            
            accounts = query.all()
            results['total_accounts'] = len(accounts)
            
            if not accounts:
                return results
            
            # Group by access token to minimize API calls
            token_groups = self._group_accounts_by_token(accounts)
            
            # Process each token group
            for access_token, token_accounts in token_groups.items():
                await self._sync_token_group(
                    access_token, token_accounts, db, results, force_sync
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Account sync failed: {e}")
            results['error'] = str(e)
            return results
    
    async def _sync_token_group(
        self, 
        access_token: str, 
        accounts: List[Account], 
        db: Session, 
        results: Dict[str, Any],
        force_sync: bool = False
    ):
        """Sync a group of accounts with the same access token"""
        
        try:
            # Fetch fresh account data from Plaid
            accounts_info = await self.fetch_accounts_and_institution(access_token)
            plaid_accounts = accounts_info.get('accounts', [])
            
            for account in accounts:
                sync_status = PlaidAccountSync(
                    account_id=str(account.id),
                    status='syncing',
                    last_sync=datetime.now(timezone.utc)
                )
                self.active_syncs[str(account.id)] = sync_status
                
                try:
                    # Skip if account doesn't need sync (unless forced)
                    if not force_sync and not account.needs_sync:
                        sync_status.status = 'skipped'
                        results['skipped'].append({
                            'account_id': str(account.id),
                            'name': account.name,
                            'reason': 'Recently synced'
                        })
                        continue
                    
                    # Find matching Plaid account
                    plaid_account = next(
                        (acc for acc in plaid_accounts 
                         if acc.get('account_id') == account.plaid_account_id),
                        None
                    )
                    
                    if not plaid_account:
                        raise Exception("Account not found in Plaid response")
                    
                    # Update account balance and metadata
                    old_balance = account.balance_dollars
                    await self._update_account_from_plaid(account, plaid_account, db)
                    
                    sync_status.status = 'synced'
                    sync_status.balance_updated = True
                    
                    results['synced'].append({
                        'account_id': str(account.id),
                        'name': account.name,
                        'old_balance': old_balance,
                        'new_balance': account.balance_dollars,
                        'change': account.balance_dollars - old_balance,
                        'sync_time': sync_status.last_sync.isoformat()
                    })
                    
                    # Send real-time notification
                    await self._send_balance_update_notification(
                        account, old_balance, account.balance_dollars
                    )
                    
                except Exception as e:
                    sync_status.status = 'error'
                    sync_status.error_message = str(e)
                    
                    account.sync_status = 'error'
                    account.last_sync_error = str(e)
                    account.connection_health = 'failed'
                    db.add(account)
                    
                    results['failed'].append({
                        'account_id': str(account.id),
                        'name': account.name,
                        'error': str(e)
                    })
                    
                    logger.error(f"Failed to sync account {account.id}: {e}")
                
                finally:
                    # Clean up sync tracking
                    if str(account.id) in self.active_syncs:
                        del self.active_syncs[str(account.id)]
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Token group sync failed: {e}")
            db.rollback()
            
            # Mark all accounts as failed
            for account in accounts:
                results['failed'].append({
                    'account_id': str(account.id),
                    'name': account.name,
                    'error': f"Token sync failed: {str(e)}"
                })
    
    async def _update_account_from_plaid(self, account: Account, plaid_account: Dict[str, Any], db: Session):
        """Update account with fresh Plaid data"""
        
        balances = plaid_account.get('balances', {})
        new_balance = balances.get('current', 0) or 0
        
        # Update account
        account.balance_cents = int(new_balance * 100)
        account.sync_status = 'synced'
        account.connection_health = 'healthy'
        account.last_sync_at = datetime.now(timezone.utc)
        account.last_sync_error = None
        
        # Update metadata
        metadata = account.account_metadata or {}
        metadata.update({
            'available_balance': balances.get('available', new_balance),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'previous_balance': account.balance_cents / 100 if account.balance_cents else 0
        })
        account.account_metadata = metadata
        
        db.add(account)
    
    async def _send_balance_update_notification(self, account: Account, old_balance: float, new_balance: float):
        """Send real-time balance update notification"""
        try:
            event = WebSocketEvent(
                type=EventType.ACCOUNT_BALANCE_UPDATED,
                data={
                    'account_id': str(account.id),
                    'account_name': account.name,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'change': new_balance - old_balance,
                    'currency': account.currency,
                    'sync_time': datetime.now(timezone.utc).isoformat()
                }
            )
            await websocket_manager.send_to_user(
                str(account.user_id),
                event.to_dict()
            )
        except Exception as e:
            logger.error(f"Failed to send balance update notification: {e}")
    
    def _group_accounts_by_token(self, accounts: List[Account]) -> Dict[str, List[Account]]:
        """Group accounts by their access token"""
        groups = {}
        for account in accounts:
            token = account.plaid_access_token
            if token not in groups:
                groups[token] = []
            groups[token].append(account)
        return groups
    
    async def sync_transactions_for_user(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Efficiently syncs transactions for all of a user's Plaid-connected accounts,
        grouping by connection to minimize API calls and avoid rate limiting.
        """
        if not self.enabled:
            return self._disabled_response()

        # 1. Get all Plaid-connected accounts for the user
        user_accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.plaid_access_token.isnot(None)
        ).all()

        if not user_accounts:
            return {"success": True, "message": "No Plaid accounts to sync.", "results": []}

        # 2. Group accounts by access token (Item)
        token_groups = self._group_accounts_by_token(user_accounts)

        # 3. Process each group
        overall_results = {
            "success": True,
            "accounts_synced": len(user_accounts),
            "total_new_transactions": 0,
            "total_updated_transactions": 0,
            "total_errors": 0,
            "results": []
        }

        for access_token, accounts_in_group in token_groups.items():
            start_time = time.time()
            try:
                # Define date range for sync (e.g., last 90 days)
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=90)
                
                plaid_account_ids = [acc.plaid_account_id for acc in accounts_in_group]

                # 4. Fetch transactions for all accounts in the group with ONE API call
                plaid_data = await self.fetch_transactions(
                    access_token, start_date, end_date, plaid_account_ids
                )
                
                # 5. Process the fetched transactions
                synced_count = await self._process_transactions(
                    plaid_data.get('transactions', []), accounts_in_group, db
                )

                overall_results["total_new_transactions"] += synced_count
                
                # Report success for each account in the group
                for account in accounts_in_group:
                    overall_results["results"].append({
                        "account_id": str(account.id),
                        "account_name": account.name,
                        "success": True,
                        "result": { "new_transactions": synced_count, "sync_duration_seconds": time.time() - start_time }
                    })

            except Exception as e:
                logger.error(f"Failed to sync transactions for token group: {e}", exc_info=True)
                overall_results["total_errors"] += len(accounts_in_group)
                # Report failure for each account in the group
                for account in accounts_in_group:
                     overall_results["results"].append({
                        "account_id": str(account.id), "account_name": account.name, "success": False, "error": str(e)
                    })
            
            # 6. Add a small delay between processing each token to be a good API citizen
            await asyncio.sleep(1) # 1-second delay

        # 7. Send a final completion event via WebSocket to trigger a dashboard refresh
        try:
            # Assuming EventType.DASHBOARD_UPDATE exists from your project documentation.
            # This event tells the frontend that dashboard-related data has changed.
            completion_event = WebSocketEvent(
                type=EventType.DASHBOARD_UPDATE,
                data={
                    "event": "sync_completed",
                    "details": overall_results
                }
            )
            await websocket_manager.send_to_user(str(user_id), completion_event.to_dict())
            logger.info(f"Sent DASHBOARD_UPDATE (sync_completed) event to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send DASHBOARD_UPDATE event to user {user_id}: {e}", exc_info=True)

        return overall_results

    async def _initial_transaction_sync(self, accounts: List[Account], access_token: str, db: Session):
        """Perform initial transaction sync for new accounts"""
        try:
            # Sync last 30 days of transactions
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            end_date = datetime.now(timezone.utc)
            
            account_ids = [acc.plaid_account_id for acc in accounts]
            
            transactions_result = await self.fetch_transactions(
                access_token, start_date, end_date, account_ids
            )
            
            synced_count = await self._process_transactions(
                transactions_result.get('transactions', []), accounts, db
            )
            
            logger.info(f"Initial sync: imported {synced_count} transactions for {len(accounts)} accounts")
            
        except Exception as e:
            logger.error(f"Initial transaction sync failed: {e}")
    
    async def fetch_transactions(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime,
        account_ids: Optional[List[str]] = None,
        count: int = 500
    ) -> Dict[str, Any]:
        """Fetch transactions from Plaid with pagination"""
        
        request_data = {
            'access_token': access_token,
            'start_date': start_date.date().isoformat(),
            'end_date': end_date.date().isoformat(),
            'options': {
                'count': count,
                'offset': 0
            }
        }
        
        if account_ids:
            request_data['options']['account_ids'] = account_ids
        
        all_transactions = []
        
        try:
            while True:
                result = await self._make_request('transactions/get', request_data)
                transactions = result.get('transactions', [])
                
                # DEBUG: Log what Plaid returned
                logger.info(f"🔍 PLAID DEBUG: API Response:")
                logger.info(f"   - Total transactions available: {result.get('total_transactions', 'Unknown')}")
                logger.info(f"   - Transactions in this batch: {len(transactions)}")
                logger.info(f"   - Current offset: {request_data['options']['offset']}")
                
                if transactions:
                    # Log first transaction as example
                    first_tx = transactions[0]
                    logger.info(f"   - Example transaction: {first_tx.get('transaction_id', 'No ID')} - ${first_tx.get('amount', 0)} - {first_tx.get('name', 'No name')}")
                else:
                    logger.info(f"   - No transactions returned by Plaid API")
                
                if not transactions:
                    break
                
                all_transactions.extend(transactions)
                
                # Check pagination
                total_transactions = result.get('total_transactions', 0)
                if len(all_transactions) >= total_transactions:
                    break
                
                request_data['options']['offset'] += len(transactions)
                
                # Prevent infinite loop
                if request_data['options']['offset'] > 10000:  # Reasonable limit
                    break
            
            # DEBUG: Log final result summary
            logger.info(f"🔍 PLAID DEBUG: Final fetch_transactions result:")
            logger.info(f"   - Total transactions fetched: {len(all_transactions)}")
            if all_transactions:
                logger.info(f"   - Date range of fetched transactions: {min(tx.get('date', '') for tx in all_transactions)} to {max(tx.get('date', '') for tx in all_transactions)}")
            
            return {
                'transactions': all_transactions,
                'accounts': result.get('accounts', []),
                'total': len(all_transactions)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            raise
    
    async def _process_transactions(
        self, 
        plaid_transactions: List[Dict[str, Any]], 
        accounts: List[Account], 
        db: Session
    ) -> int:
        """Process and save Plaid transactions to database"""
        
        # Create account ID mapping
        account_map = {acc.plaid_account_id: acc for acc in accounts}
        synced_count = 0
        
        for plaid_txn in plaid_transactions:
            try:
                account_id = plaid_txn.get('account_id')
                account = account_map.get(account_id)
                
                if not account:
                    continue
                
                # Check if transaction already exists
                existing = db.query(Transaction).filter(
                    Transaction.plaid_transaction_id == plaid_txn.get('transaction_id')
                ).first()
                
                if existing:
                    continue
                
                # Create transaction
                transaction = await self._create_transaction_from_plaid(plaid_txn, account, db)
                if transaction:
                    synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process transaction {plaid_txn.get('transaction_id', 'unknown')}: {e}")
        
        db.commit()
        return synced_count
    
    def _determine_transaction_type(self, plaid_txn: Dict[str, Any], amount: float) -> str:
        """Determine if transaction is income or expense based on Plaid data"""
        
        # Get transaction details
        name = plaid_txn.get('name', '').lower()
        categories = plaid_txn.get('category', [])
        account_owner = plaid_txn.get('account_owner', '')
        
        # Plaid amount convention: positive = debit (money out), negative = credit (money in)
        # So negative amounts are typically income
        if amount < 0:
            # Negative Plaid amount suggests money coming in (credit)
            # Check for income patterns
            income_patterns = [
                'ach electronic credit', 'direct deposit', 'payroll', 'salary',
                'transfer from', 'deposit', 'refund', 'cashback', 'interest',
                'dividend', 'pension', 'unemployment', 'social security',
                'tax refund', 'insurance claim', 'bonus'
            ]
            
            # Check categories for income types
            income_categories = [
                'Deposit', 'Transfer', 'Payroll', 'Interest', 'Dividend',
                'Refund', 'Reward', 'Credit'
            ]
            
            # Check if any category suggests income
            for category in categories:
                if any(inc_cat.lower() in category.lower() for inc_cat in income_categories):
                    return 'income'
            
            # Check name for income patterns
            if any(pattern in name for pattern in income_patterns):
                return 'income'
            
            # If negative amount but no clear income indicators, could be refund/credit
            return 'income'  # Default negative amounts to income
        else:
            # Positive Plaid amount suggests money going out (debit)
            # This is typically an expense, but double-check for transfers
            
            transfer_patterns = [
                'transfer to', 'payment to', 'online transfer', 'internal transfer'
            ]
            
            # Check if this is a transfer (might want different handling)
            if any(pattern in name for pattern in transfer_patterns):
                # For now, treat transfers as expenses, but we could add transfer logic later
                return 'expense'
            
            # Default positive amounts to expense
            return 'expense'
    
    async def _create_transaction_from_plaid(
        self, 
        plaid_txn: Dict[str, Any], 
        account: Account, 
        db: Session
    ) -> Optional[Transaction]:
        """Create a transaction from Plaid data"""
        
        try:
            # Parse transaction data
            amount = float(plaid_txn.get('amount', 0))
            
            # Determine transaction type based on Plaid data
            transaction_type = self._determine_transaction_type(plaid_txn, amount)
            
            # Convert to cents - let the schema handle the sign based on transaction_type
            amount_cents = int(abs(amount) * 100)
            
            transaction_date = datetime.fromisoformat(
                plaid_txn.get('date', datetime.now(timezone.utc).date().isoformat())
            ).replace(tzinfo=timezone.utc)
            
            transaction_create = TransactionCreate(
                user_id=account.user_id,
                account_id=account.id,
                amount_cents=amount_cents,
                currency=account.currency,
                description=plaid_txn.get('name', 'Unknown Transaction'),
                transaction_date=transaction_date,
                merchant=plaid_txn.get('merchant_name'),
                plaid_transaction_id=plaid_txn.get('transaction_id'),
                plaid_category=plaid_txn.get('category', []),
                transaction_type=transaction_type,  # Add transaction type
                metadata_json={
                    'plaid_data': plaid_txn,
                    'imported_at': datetime.now(timezone.utc).isoformat(),
                    'sync_method': 'initial_import',
                    'original_plaid_amount': amount,  # Store original for debugging
                    'determined_type': transaction_type
                }
            )
            
            # Use the TransactionService API to create a transaction (with ML integration)
            transaction = await self.transaction_service.create_transaction(
                db, transaction_create, account.user_id
            )
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create transaction from Plaid data: {e}")
            return None
    
    async def get_sync_status(self, account_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get current sync status for accounts"""
        
        if account_ids:
            relevant_syncs = {
                k: v for k, v in self.active_syncs.items() 
                if k in account_ids
            }
        else:
            relevant_syncs = self.active_syncs
        
        return {
            'active_syncs': len(relevant_syncs),
            'syncs': {
                account_id: {
                    'status': sync.status,
                    'last_sync': sync.last_sync.isoformat() if sync.last_sync else None,
                    'error_message': sync.error_message,
                    'transactions_synced': sync.transactions_synced,
                    'balance_updated': sync.balance_updated
                }
                for account_id, sync in relevant_syncs.items()
            }
        }
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Plaid API"""
        if not self.enabled:
            raise Exception("Plaid integration is disabled")
        
        url = f"{self.base_url}/{endpoint}"
        
        # Add authentication
        data.update({
            'client_id': self.client_id,
            'secret': self.secret
        })
        
        logger.debug(f"Making Plaid API request to {url} with data: {data}")
        
        try:
            # Use asyncio for non-blocking requests
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=data, timeout=30)
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Plaid API request failed: {e}")
            # Try to get the actual error response
            error_detail = "Unknown error"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.text
                    logger.error(f"Plaid API error response: {error_detail}")
                except:
                    pass
            raise Exception(f"Plaid API error: {str(e)} - Detail: {error_detail}")
    
    async def get_connection_status(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get connection status for user's Plaid accounts"""
        if not self.enabled:
            return self._disabled_response()
        
        try:
            from app.models.account import Account
            
            # Get user's Plaid-connected accounts
            plaid_accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.plaid_account_id.isnot(None)
            ).all()
            
            if not plaid_accounts:
                return {
                    'total_connections': 0,
                    'active_connections': 0,
                    'failed_connections': 0,
                    'needs_reauth': 0,
                    'accounts': [],
                    'message': 'No Plaid accounts connected'
                }
            
            # Check account statuses and format for frontend
            formatted_accounts = []
            active_connections = 0
            failed_connections = 0
            needs_reauth = 0
            
            for account in plaid_accounts:
                # Determine health status based on metadata and last sync
                metadata = account.account_metadata or {}
                last_sync = metadata.get('last_sync')
                health_status = 'unknown'
                
                if last_sync:
                    try:
                        # Parse the timestamp and ensure it's timezone-aware
                        if last_sync.endswith('Z'):
                            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                        elif '+' in last_sync or last_sync.endswith('00'):
                            last_sync_dt = datetime.fromisoformat(last_sync)
                        else:
                            # Assume UTC if no timezone info
                            last_sync_dt = datetime.fromisoformat(last_sync).replace(tzinfo=timezone.utc)
                        
                        # Calculate hours since sync using timezone-aware datetime
                        now_utc = datetime.now(timezone.utc)
                        hours_since_sync = (now_utc - last_sync_dt).total_seconds() / 3600
                        
                        if hours_since_sync < 24:
                            health_status = 'healthy'
                            active_connections += 1
                        elif hours_since_sync < 168:  # 1 week
                            health_status = 'warning'
                        else:
                            health_status = 'failed'
                            failed_connections += 1
                    except (ValueError, AttributeError):
                        health_status = 'unknown'
                        failed_connections += 1
                else:
                    health_status = 'unknown'
                    failed_connections += 1
                
                # Format account for frontend
                account_data = {
                    'account_id': str(account.id),
                    'name': account.name,
                    'type': account.account_type,
                    'health_status': health_status,
                    'last_sync': last_sync,
                    'balance': account.balance_cents / 100.0,  # Convert cents to dollars
                    'currency': account.currency,
                    'plaid_account_id': account.plaid_account_id
                }
                
                formatted_accounts.append(account_data)
            
            return {
                'total_connections': len(plaid_accounts),
                'active_connections': active_connections,
                'failed_connections': failed_connections,
                'needs_reauth': needs_reauth,
                'accounts': formatted_accounts
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve connection status'
            }
    
    def _disabled_response(self) -> Dict[str, Any]:
        """Standard response when Plaid is disabled"""
        return {
            'success': False,
            'error': 'Plaid integration is disabled',
            'message': 'Set ENABLE_PLAID=true and configure credentials to enable Plaid integration'
        }

# Create global enhanced service instance
enhanced_plaid_service = EnhancedPlaidService()