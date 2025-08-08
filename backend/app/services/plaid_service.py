"""
Plaid integration service for bank account connections and transaction sync
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import requests
import json

from app.config import settings
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.transaction import TransactionCreate
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

class PlaidService:
    """Service for Plaid bank integration and automatic sync"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'ENABLE_PLAID', False)
        self.client_id = getattr(settings, 'PLAID_CLIENT_ID', '')
        self.secret = getattr(settings, 'PLAID_SECRET', '')
        self.environment = getattr(settings, 'PLAID_ENV', 'sandbox')
        
        if not self.enabled:
            logger.info("Plaid integration is disabled (ENABLE_PLAID=false)")
            return
        
        # Plaid API endpoints
        self.base_url = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }.get(self.environment, 'https://sandbox.plaid.com')
        
        self.account_service = AccountService()
        self.transaction_service = TransactionService()
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Plaid API"""
        if not self.enabled:
            raise Exception("Plaid integration is disabled. Set ENABLE_PLAID=true to enable.")
        
        if not self.client_id or not self.secret:
            raise Exception("Plaid credentials not configured. Please set PLAID_CLIENT_ID and PLAID_SECRET.")
            
        url = f"{self.base_url}/{endpoint}"
        
        # Add authentication
        data.update({
            'client_id': self.client_id,
            'secret': self.secret
        })
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Plaid API request failed: {e}")
            raise Exception(f"Plaid API error: {str(e)}")
    
    async def create_link_token(self, user_id: str) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization"""
        if not self.enabled:
            return {
                'error': 'Plaid integration is disabled',
                'message': 'Set ENABLE_PLAID=true in your environment to enable Plaid integration'
            }
        
        try:
            data = {
                'user': {'client_user_id': str(user_id)},
                'client_name': 'Finance Tracker',
                'products': ['transactions'],
                'country_codes': ['US'],
                'language': 'en',
                'webhook': f"{settings.FRONTEND_URL}/api/webhooks/plaid" if hasattr(settings, 'FRONTEND_URL') else None
            }
            
            result = self._make_request('link/token/create', data)
            return {
                'link_token': result.get('link_token'),
                'expiration': result.get('expiration'),
                'request_id': result.get('request_id')
            }
        except Exception as e:
            logger.error(f"Failed to create link token: {e}")
            raise
    
    async def exchange_public_token(self, public_token: str, user_id: str, db: Session) -> Dict[str, Any]:
        """Exchange public token for access token and create accounts"""
        if not self.enabled:
            return {
                'error': 'Plaid integration is disabled',
                'message': 'Set ENABLE_PLAID=true in your environment to enable Plaid integration'
            }
        
        try:
            # Exchange public token
            data = {'public_token': public_token}
            result = self._make_request('link/token/exchange', data)
            
            access_token = result.get('access_token')
            item_id = result.get('item_id')
            
            if not access_token:
                raise Exception("No access token received from Plaid")
            
            # Get account information
            accounts_info = await self.fetch_accounts(access_token)
            
            # Create accounts in database
            created_accounts = []
            for account_data in accounts_info.get('accounts', []):
                account = await self._create_account_from_plaid(
                    account_data, access_token, item_id, user_id, db
                )
                created_accounts.append(account)
            
            return {
                'access_token': access_token,
                'item_id': item_id,
                'accounts': created_accounts,
                'institution': accounts_info.get('institution')
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange public token: {e}")
            raise
    
    async def fetch_accounts(self, access_token: str) -> Dict[str, Any]:
        """Fetch account information from Plaid"""
        if not self.enabled:
            return {
                'error': 'Plaid integration is disabled',
                'accounts': [],
                'institution': None
            }
        
        try:
            data = {'access_token': access_token}
            accounts_result = self._make_request('accounts/get', data)
            
            # Get institution info
            item_data = {'access_token': access_token}
            item_result = self._make_request('item/get', data)
            
            institution_id = item_result.get('item', {}).get('institution_id')
            institution_info = None
            
            if institution_id:
                inst_data = {
                    'institution_id': institution_id,
                    'country_codes': ['US']
                }
                inst_result = self._make_request('institutions/get_by_id', inst_data)
                institution_info = inst_result.get('institution')
            
            return {
                'accounts': accounts_result.get('accounts', []),
                'institution': institution_info,
                'item': item_result.get('item')
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            raise
    
    async def _create_account_from_plaid(
        self, 
        plaid_account: Dict[str, Any], 
        access_token: str, 
        item_id: str, 
        user_id: str, 
        db: Session
    ) -> Account:
        """Create account from Plaid account data"""
        
        # Map Plaid account types to our types
        type_mapping = {
            'depository': {
                'checking': 'checking',
                'savings': 'savings',
                'cd': 'savings',
                'money market': 'savings'
            },
            'credit': {
                'credit card': 'credit_card'
            },
            'loan': {
                'mortgage': 'mortgage',
                'auto': 'loan',
                'student': 'loan'
            },
            'investment': {
                'brokerage': 'investment',
                '401k': 'retirement',
                'ira': 'retirement'
            }
        }
        
        plaid_type = plaid_account.get('type', '').lower()
        plaid_subtype = plaid_account.get('subtype', '').lower()
        
        account_type = 'checking'  # default
        if plaid_type in type_mapping:
            if plaid_subtype in type_mapping[plaid_type]:
                account_type = type_mapping[plaid_type][plaid_subtype]
            else:
                # Use first available type for this category
                account_type = list(type_mapping[plaid_type].values())[0]
        
        # Get current balance
        balances = plaid_account.get('balances', {})
        current_balance = balances.get('current', 0)
        available_balance = balances.get('available', current_balance)
        
        account_create = AccountCreate(
            user_id=user_id,
            name=plaid_account.get('name', 'Unknown Account'),
            account_type=account_type,
            balance_cents=int(current_balance * 100) if current_balance else 0,
            currency=balances.get('iso_currency_code', 'USD'),
            is_active=True,
            plaid_account_id=plaid_account.get('account_id'),
            plaid_access_token=access_token,
            plaid_item_id=item_id,
            account_metadata={
                'plaid_type': plaid_type,
                'plaid_subtype': plaid_subtype,
                'mask': plaid_account.get('mask'),
                'official_name': plaid_account.get('official_name'),
                'available_balance': available_balance,
                'last_sync': datetime.utcnow().isoformat()
            }
        )
        
        account = self.account_service.create(db=db, obj_in=account_create)
        logger.info(f"Created Plaid account: {account.name} ({account.id})")
        
        return account
    
    async def sync_account_balances(self, db: Session, account_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sync account balances from Plaid"""
        if not self.enabled:
            return {
                'synced': [],
                'failed': [],
                'total_accounts': 0,
                'message': 'Plaid integration is disabled'
            }
        
        results = {
            'synced': [],
            'failed': [],
            'total_accounts': 0
        }
        
        try:
            # Get accounts to sync
            if account_ids:
                accounts = [self.account_service.get(db=db, id=acc_id) for acc_id in account_ids]
                accounts = [acc for acc in accounts if acc and acc.plaid_access_token]
            else:
                accounts = db.query(Account).filter(
                    Account.plaid_access_token.isnot(None),
                    Account.is_active == True
                ).all()
            
            results['total_accounts'] = len(accounts)
            
            # Group by access token to minimize API calls
            token_groups = {}
            for account in accounts:
                token = account.plaid_access_token
                if token not in token_groups:
                    token_groups[token] = []
                token_groups[token].append(account)
            
            # Sync each token group
            for access_token, token_accounts in token_groups.items():
                try:
                    plaid_accounts = await self.fetch_accounts(access_token)
                    
                    for account in token_accounts:
                        try:
                            # Find matching Plaid account
                            plaid_account = next(
                                (acc for acc in plaid_accounts.get('accounts', []) 
                                 if acc.get('account_id') == account.plaid_account_id),
                                None
                            )
                            
                            if plaid_account:
                                # Update balance
                                balances = plaid_account.get('balances', {})
                                new_balance = balances.get('current', 0)
                                
                                old_balance = account.balance_cents / 100
                                account.balance_cents = int(new_balance * 100)
                                
                                # Update metadata
                                metadata = account.account_metadata or {}
                                metadata.update({
                                    'available_balance': balances.get('available', new_balance),
                                    'last_sync': datetime.utcnow().isoformat(),
                                    'previous_balance': old_balance
                                })
                                account.account_metadata = metadata
                                
                                db.add(account)
                                
                                results['synced'].append({
                                    'account_id': str(account.id),
                                    'name': account.name,
                                    'old_balance': old_balance,
                                    'new_balance': new_balance,
                                    'change': new_balance - old_balance
                                })
                                
                                logger.info(f"Synced balance for {account.name}: ${old_balance:.2f} -> ${new_balance:.2f}")
                            
                        except Exception as e:
                            logger.error(f"Failed to sync account {account.id}: {e}")
                            results['failed'].append({
                                'account_id': str(account.id),
                                'error': str(e)
                            })
                
                except Exception as e:
                    logger.error(f"Failed to fetch accounts for token: {e}")
                    for account in token_accounts:
                        results['failed'].append({
                            'account_id': str(account.id),
                            'error': f"Token fetch failed: {str(e)}"
                        })
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Account balance sync failed: {e}")
            db.rollback()
            raise
        
        return results
    
    async def fetch_transactions(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime,
        account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch transactions from Plaid"""
        try:
            data = {
                'access_token': access_token,
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'count': 500,
                'offset': 0
            }
            
            if account_ids:
                data['account_ids'] = account_ids
            
            all_transactions = []
            
            # Paginate through all transactions
            while True:
                result = self._make_request('transactions/get', data)
                transactions = result.get('transactions', [])
                
                if not transactions:
                    break
                
                all_transactions.extend(transactions)
                
                # Check if we have more transactions
                total_transactions = result.get('total_transactions', 0)
                if len(all_transactions) >= total_transactions:
                    break
                
                data['offset'] += len(transactions)
            
            return {
                'transactions': all_transactions,
                'accounts': result.get('accounts', []),
                'total': len(all_transactions)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            raise
    
    def get_connection_status(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Get connection status for all user's Plaid accounts"""
        if not self.enabled:
            return {
                'total_connections': 0,
                'active_connections': 0,
                'failed_connections': 0,
                'needs_reauth': 0,
                'accounts': [],
                'message': 'Plaid integration is disabled'
            }
        
        try:
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.plaid_access_token.isnot(None)
            ).all()
            
            status = {
                'total_connections': len(accounts),
                'active_connections': 0,
                'failed_connections': 0,
                'needs_reauth': 0,
                'accounts': []
            }
            
            for account in accounts:
                metadata = account.account_metadata or {}
                last_sync = metadata.get('last_sync')
                
                # Determine connection health
                health_status = 'unknown'
                if last_sync:
                    last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', ''))
                    hours_since_sync = (datetime.utcnow() - last_sync_dt).total_seconds() / 3600
                    
                    if hours_since_sync < 24:
                        health_status = 'healthy'
                        status['active_connections'] += 1
                    elif hours_since_sync < 168:  # 1 week
                        health_status = 'warning'
                    else:
                        health_status = 'failed'
                        status['failed_connections'] += 1
                
                account_status = {
                    'account_id': str(account.id),
                    'name': account.name,
                    'type': account.account_type,
                    'health_status': health_status,
                    'last_sync': last_sync,
                    'balance': account.balance_cents / 100,
                    'currency': account.currency,
                    'plaid_account_id': account.plaid_account_id
                }
                
                status['accounts'].append(account_status)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            raise

# Create global service instance
plaid_service = PlaidService()