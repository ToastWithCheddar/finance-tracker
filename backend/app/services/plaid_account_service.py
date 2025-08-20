"""
Plaid Account Service
Handles account creation, updating, balance synchronization, and account management
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.account import Account
from app.schemas.account import AccountCreate
from app.services.account_service import AccountService
from app.services.account_alert_service import account_alert_service
from app.services.plaid_client_service import plaid_client_service
from app.services.utils.plaid_utils import group_accounts_by_token
from app.websocket.manager import redis_websocket_manager as websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)


class PlaidAccountService:
    """Service for managing Plaid-connected accounts"""
    
    def __init__(self):
        self.account_service = AccountService()
    
    async def create_or_update_account(
        self, 
        plaid_account: Dict[str, Any], 
        access_token: str, 
        item_id: str, 
        user_id: UUID, 
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
        user_id: UUID, 
        db: Session,
        institution_info: Optional[Dict[str, Any]] = None
    ) -> Account:
        """Create a new account from Plaid data"""
        
        # Lightweight type assertion for internal bug detection
        if not isinstance(user_id, UUID):
            raise TypeError(f"user_id must be UUID, got {type(user_id)}")
        
        logger.debug(f"Creating account for user {user_id}, Plaid account: {plaid_account.get('account_id')}")
        
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
        
        # Application-level deduplication guard
        try:
            potential_duplicate = db.query(Account).filter(
                Account.user_id == user_id,
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
                f"Found potential duplicate account for user {user_id}: {potential_duplicate.id}. Updating instead of creating."
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
        logger.info(f"Creating AccountCreate object - User UUID: {user_id}, Account: {account_name}, Plaid ID: {plaid_account_id}")
        
        try:
            account_create = AccountCreate(
                user_id=user_id,
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
        old_balance = account.balance_cents / 100 if account.balance_cents else 0
        
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
            'previous_balance': old_balance
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
        
        # Send balance update notification if balance changed significantly
        if abs(new_balance - old_balance) > 0.01:  # More than 1 cent
            await self._send_balance_update_notification(account, old_balance, new_balance)
        
        logger.info(f"Updated Plaid account: {account.name} ({account.id})")
        return account
    
    async def sync_account_balances(
        self, 
        db: Session, 
        account_ids: Optional[List[str]] = None,
        user_id: Optional[UUID] = None,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """Enhanced account balance synchronization with real-time updates"""
        
        results = {
            'synced': [],
            'failed': [],
            'skipped': [],
            'total_accounts': 0,
            'sync_time': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Get accounts to sync
            query = db.query(Account).filter(Account.plaid_access_token_encrypted.isnot(None))
            
            if account_ids:
                query = query.filter(Account.id.in_(account_ids))
            
            if user_id:
                query = query.filter(Account.user_id == user_id)
            
            accounts = query.all()
            results['total_accounts'] = len(accounts)
            
            if not accounts:
                return results
            
            # Group by access token to minimize API calls
            token_groups = group_accounts_by_token(accounts)
            
            # Process each token group
            for access_token, token_accounts in token_groups.items():
                try:
                    await self._sync_token_group(access_token, token_accounts, db, results, force_sync)
                except Exception as e:
                    logger.error(f"Failed to sync token group: {e}")
                    for account in token_accounts:
                        results['failed'].append({
                            'account_id': str(account.id),
                            'account_name': account.name,
                            'error': f"Token group sync failed: {str(e)}"
                        })
            
            logger.info(f"Balance sync completed: {len(results['synced'])} synced, {len(results['failed'])} failed")
            return results
            
        except Exception as e:
            logger.error(f"Account balance sync failed: {e}")
            results['error'] = str(e)
            return results
    
    async def _sync_token_group(
        self, 
        access_token: str, 
        accounts: List[Account], 
        db: Session, 
        results: Dict[str, Any],
        force_sync: bool = False
    ) -> None:
        """Sync balances for a group of accounts with the same access token"""
        try:
            # Fetch fresh balances from Plaid
            balance_response = await plaid_client_service.fetch_account_balances(access_token)
            
            if not balance_response.get('success'):
                raise Exception(balance_response.get('error', 'Unknown error'))
            
            plaid_accounts = balance_response.get('accounts', [])
            plaid_account_map = {acc['account_id']: acc for acc in plaid_accounts}
            
            # Update each account
            for account in accounts:
                try:
                    # Check if sync is needed (unless force_sync is True)
                    if not force_sync and not account.needs_sync:
                        results['skipped'].append({
                            'account_id': str(account.id),
                            'account_name': account.name,
                            'reason': 'Recently synced, use force_sync=True to override'
                        })
                        continue
                    
                    plaid_account = plaid_account_map.get(account.plaid_account_id)
                    if not plaid_account:
                        results['failed'].append({
                            'account_id': str(account.id),
                            'account_name': account.name,
                            'error': 'Account not found in Plaid response'
                        })
                        continue
                    
                    await self._update_account_from_plaid(account, plaid_account, db)
                    
                    results['synced'].append({
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'balance': account.balance_cents / 100,
                        'sync_time': datetime.now(timezone.utc).isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to update account {account.id}: {e}")
                    results['failed'].append({
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'error': str(e)
                    })
            
        except Exception as e:
            logger.error(f"Failed to fetch balances for token group: {e}")
            raise
    
    async def _update_account_from_plaid(self, account: Account, plaid_account: Dict[str, Any], db: Session):
        """Update a single account from Plaid data"""
        balances = plaid_account.get('balances', {})
        new_balance = balances.get('current', 0) or 0
        old_balance = account.balance_cents / 100 if account.balance_cents else 0
        
        # Update balance and sync info
        account.balance_cents = int(new_balance * 100)
        account.last_sync_at = datetime.now(timezone.utc)
        account.sync_status = 'synced'
        account.connection_health = 'healthy'
        
        # Update metadata
        metadata = account.account_metadata or {}
        metadata.update({
            'available_balance': balances.get('available', new_balance),
            'last_sync': datetime.now(timezone.utc).isoformat(),
            'previous_balance': old_balance
        })
        account.account_metadata = metadata
        
        db.add(account)
        db.commit()
        
        # Send notification if balance changed significantly
        if abs(new_balance - old_balance) > 0.01:
            await self._send_balance_update_notification(account, old_balance, new_balance)
    
    async def _send_balance_update_notification(self, account: Account, old_balance: float, new_balance: float):
        """Send real-time notification for balance updates"""
        try:
            balance_change = new_balance - old_balance
            
            # Create WebSocket event
            event = WebSocketEvent(
                type=EventType.ACCOUNT_BALANCE_UPDATED,
                data={
                    'account_id': str(account.id),
                    'account_name': account.name,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'change': balance_change,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Send to user's WebSocket connections
            await websocket_manager.send_to_user(str(account.user_id), event)
            
            # Check for account alerts
            await account_alert_service.check_balance_alerts(account, new_balance)
            
        except Exception as e:
            logger.error(f"Failed to send balance update notification: {e}")
    
    
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


# Create singleton instance
plaid_account_service = PlaidAccountService()