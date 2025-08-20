"""
Plaid Orchestration Service
Main service that orchestrates all Plaid-related operations by coordinating the specialized services
Maintains compatibility with existing interface while delegating to focused services
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.account import Account
from app.services.plaid_client_service import plaid_client_service
from app.services.plaid_account_service import plaid_account_service
from app.services.plaid_transaction_service import plaid_transaction_service
from app.services.plaid_webhook_service import plaid_webhook_service

logger = logging.getLogger(__name__)


class PlaidOrchestrationService:
    """
    Main Plaid service that orchestrates all Plaid operations
    Maintains the same interface as the original EnhancedPlaidService for backward compatibility
    """
    
    def __init__(self):
        self.enabled = plaid_client_service.enabled
    
    # Token and Link Management (delegated to client service)
    async def create_link_token(self, user_id: str, update_mode: bool = False) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization or update"""
        return await plaid_client_service.create_link_token(user_id, update_mode)
    
    async def exchange_public_token(self, public_token: str, user_id: UUID, db: Session) -> Dict[str, Any]:
        """Exchange public token for access token and create accounts with robust error handling"""
        if not self.enabled:
            return self._disabled_response()
        
        if not isinstance(user_id, UUID):
            raise TypeError(f"user_id must be UUID, got {type(user_id)}")
        
        logger.info(f"Starting token exchange for user: {user_id}")
        
        # Initialize variables for cleanup
        created_accounts = []
        access_token = None
        item_id = None
        
        try:
            # Step 1: Exchange token via client service
            logger.debug("Step 1: Exchanging public token")
            exchange_result = await plaid_client_service.exchange_public_token(public_token)
            
            if not exchange_result.get('success'):
                logger.error(f"Token exchange failed: {exchange_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': exchange_result.get('error', 'Token exchange failed'),
                    'message': exchange_result.get('message', 'Failed to connect bank account. Please try again.'),
                    'error_type': 'plaid_api_error',
                    'accounts': []
                }
            
            access_token = exchange_result.get('access_token')
            item_id = exchange_result.get('item_id')
            
            if not access_token or not item_id:
                logger.error("Token exchange succeeded but missing access_token or item_id")
                return {
                    'success': False,
                    'error': 'Invalid response from Plaid API',
                    'message': 'Failed to connect bank account. Please try again.',
                    'error_type': 'plaid_response_error',
                    'accounts': []
                }
            
            logger.info(f"Successfully exchanged token, got access_token and item_id: {item_id}")
            
            # Step 2: Get accounts and institution info via client service
            logger.debug("Step 2: Fetching accounts and institution information")
            accounts_info = await plaid_client_service.fetch_accounts_and_institution(access_token)
            
            if not accounts_info or not accounts_info.get('accounts'):
                logger.error("No accounts found in Plaid response")
                return {
                    'success': False,
                    'error': 'No accounts found',
                    'message': 'No bank accounts found to connect. Please try again.',
                    'error_type': 'no_accounts_error',
                    'accounts': []
                }
            
            logger.info(f"Fetched {len(accounts_info.get('accounts', []))} accounts from Plaid")
            institution_info = accounts_info.get('institution')
            
            # Step 3: Create accounts in database within a single transaction
            logger.debug("Step 3: Creating accounts in database")
            
            # Process each account within the database transaction
            for account_data in accounts_info.get('accounts', []):
                logger.info(f"Processing account: {account_data.get('account_id', 'unknown')}")
                account = await plaid_account_service.create_or_update_account(
                    account_data, access_token, item_id, user_id, db, institution_info
                )
                created_accounts.append(account)
                logger.info(f"Successfully processed account: {account.name} (ID: {account.id})")
            
            # Commit the transaction after all accounts are created
            db.commit()
            logger.info(f"Successfully committed {len(created_accounts)} accounts to database")
            
            # Step 4: Initial sync of recent transactions (non-critical, don't fail on errors)
            logger.debug("Step 4: Running initial transaction sync")
            try:
                await plaid_transaction_service.initial_transaction_sync(created_accounts, access_token, db)
                logger.info("Initial transaction sync completed successfully")
            except Exception as sync_error:
                logger.warning(f"Initial transaction sync failed, but accounts were created successfully: {sync_error}")
                # Don't fail the whole process if transaction sync fails - this is non-critical
            
            # Success response
            return {
                'success': True,
                'access_token': access_token,
                'item_id': item_id,
                'accounts': created_accounts,
                'institution': institution_info,
                'accounts_created': len(created_accounts),
                'message': f"Successfully connected {len(created_accounts)} accounts"
            }
            
        except Exception as e:
            # Comprehensive error handling with proper rollback and categorization
            error_message = str(e)
            error_type = 'unknown_error'
            user_message = 'Failed to connect bank account. Please try again.'
            
            # Categorize the error for better debugging and handling
            if 'plaid' in error_message.lower() or 'api' in error_message.lower():
                error_type = 'plaid_api_error'
                user_message = 'Bank connection service is temporarily unavailable. Please try again later.'
            elif 'database' in error_message.lower() or 'constraint' in error_message.lower():
                error_type = 'database_error'
                user_message = 'Failed to save account information. Please try again.'
            elif 'network' in error_message.lower() or 'connection' in error_message.lower():
                error_type = 'network_error'
                user_message = 'Network connection failed. Please check your internet and try again.'
            elif 'timeout' in error_message.lower():
                error_type = 'timeout_error'
                user_message = 'Request timed out. Please try again.'
            
            logger.error(
                f"Token exchange failed for user {user_id}. Error type: {error_type}. Error: {error_message}", 
                exc_info=True,
                extra={
                    'user_id': user_id,
                    'error_type': error_type,
                    'access_token_received': access_token is not None,
                    'item_id_received': item_id is not None,
                    'accounts_created_count': len(created_accounts)
                }
            )
            
            # Ensure database rollback on any error
            try:
                db.rollback()
                logger.debug("Database transaction rolled back successfully")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback database transaction: {rollback_error}")
                # This is a critical error - database is potentially in inconsistent state
                error_type = 'critical_database_error'
                user_message = 'Critical error occurred. Please contact support.'
            
            return {
                'success': False,
                'error': error_message,
                'error_type': error_type,
                'message': user_message,
                'accounts': [],
                'debug_info': {
                    'step_reached': 'token_exchange' if not access_token else (
                        'account_fetch' if not created_accounts else 'database_commit'
                    ),
                    'accounts_processed': len(created_accounts)
                }
            }
    
    # Account Management (delegated to account service)
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
        
        return await plaid_account_service.sync_account_balances(
            db, account_ids, user_id, force_sync
        )
    
    async def fetch_accounts_and_institution(self, access_token: str) -> Dict[str, Any]:
        """Fetch comprehensive account and institution information"""
        return await plaid_client_service.fetch_accounts_and_institution(access_token)
    
    # Transaction Management (delegated to transaction service)
    async def sync_transactions_for_user(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Efficiently syncs transactions for all of a user's Plaid-connected accounts,
        grouping by connection to minimize API calls and avoid rate limiting.
        """
        if not self.enabled:
            return self._disabled_response()
        
        return await plaid_transaction_service.sync_transactions_for_user(db, user_id)
    
    async def fetch_transactions(
        self, 
        access_token: str, 
        start_date: datetime, 
        end_date: datetime,
        account_ids: Optional[List[str]] = None,
        count: int = 500
    ) -> Dict[str, Any]:
        """Fetch transactions from Plaid with pagination"""
        return await plaid_transaction_service.fetch_transactions(
            access_token, start_date, end_date, account_ids, count
        )
    
    # Recurring Transactions (delegated to webhook service)
    async def fetch_recurring_transactions(self, access_token: str) -> Dict[str, Any]:
        """Fetch recurring transactions using Plaid's /transactions/recurring/get endpoint"""
        if not self.enabled:
            return self._disabled_response()
        
        return await plaid_client_service.fetch_recurring_transactions(access_token)
    
    async def sync_recurring_transactions_for_user(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Sync all recurring transactions for a user's accounts"""
        # Lightweight type assertion for internal bug detection
        if not isinstance(user_id, UUID):
            raise TypeError(f"user_id must be UUID, got {type(user_id)}")
            
        if not self.enabled:
            return self._disabled_response()
        
        return await plaid_webhook_service.sync_recurring_transactions_for_user(db, user_id)
    
    # Connection Status and Health
    async def get_connection_status(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive connection status for all user's Plaid accounts"""
        # Lightweight type assertion for internal bug detection
        if not isinstance(user_id, UUID):
            raise TypeError(f"user_id must be UUID, got {type(user_id)}")
            
        if not self.enabled:
            return self._disabled_response()
        
        try:
            # Get all user's Plaid accounts
            accounts = db.query(Account).filter(
                Account.user_id == user_id,
                Account.plaid_access_token_encrypted.isnot(None)
            ).all()
            
            if not accounts:
                return {
                    'success': True,
                    'message': 'No Plaid accounts found',
                    'accounts': [],
                    'overall_status': 'no_accounts'
                }
            
            # Group by access token to check each connection
            token_groups = {}
            for account in accounts:
                token = account.plaid_access_token
                if token not in token_groups:
                    token_groups[token] = []
                token_groups[token].append(account)
            
            connection_results = []
            overall_healthy = True
            
            for access_token, token_accounts in token_groups.items():
                try:
                    # Check connection status via client service
                    status_result = await plaid_client_service.get_connection_status(access_token)
                    
                    if not status_result.get('success'):
                        overall_healthy = False
                    
                    # Add account info to result
                    for account in token_accounts:
                        connection_results.append({
                            'account_id': str(account.id),
                            'account_name': account.name,
                            'connection_status': status_result.get('status', 'unknown'),
                            'last_sync': account.last_sync_at.isoformat() if account.last_sync_at else None,
                            'sync_status': account.sync_status,
                            'connection_health': account.connection_health,
                            'error': status_result.get('error'),
                            'institution_name': account.account_metadata.get('institution_name') if account.account_metadata else None
                        })
                
                except Exception as e:
                    logger.error(f"Failed to check connection status for token group: {e}")
                    overall_healthy = False
                    for account in token_accounts:
                        connection_results.append({
                            'account_id': str(account.id),
                            'account_name': account.name,
                            'connection_status': 'error',
                            'error': str(e)
                        })
            
            return {
                'success': True,
                'accounts': connection_results,
                'overall_status': 'healthy' if overall_healthy else 'issues_detected',
                'total_accounts': len(accounts),
                'healthy_accounts': len([r for r in connection_results if r.get('connection_status') == 'healthy'])
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection status for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to check connection status'
            }
    
    async def get_sync_status(self, account_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get sync status for accounts"""
        if not self.enabled:
            return self._disabled_response()
        
        # This would typically check active sync operations
        # For now, return a simple status
        return {
            'success': True,
            'active_syncs': [],
            'message': 'No active syncs'
        }
    
    # Webhook Handling (delegated to webhook service)
    async def handle_webhook(self, webhook_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Handle incoming Plaid webhook"""
        return await plaid_webhook_service.handle_webhook(webhook_data, db)
    
    # Utility methods
    def _disabled_response(self) -> Dict[str, Any]:
        """Standard response when Plaid is disabled"""
        return plaid_client_service._disabled_response()


