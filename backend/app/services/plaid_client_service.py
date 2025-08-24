"""
Core Plaid Client Service
Handles low-level Plaid API communication, authentication, and basic token operations
"""

import logging
from typing import Dict, Any, Optional
import requests
import json
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class PlaidClientService:
    """Core Plaid API client for low-level operations"""
    
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
            
        # Validate configuration - strict validation for credentials
        self._validate_configuration()
        
        # Plaid API endpoints
        self.base_url = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }.get(self.environment, 'https://sandbox.plaid.com')
        
        logger.info(f"Plaid client service initialized for {self.environment} environment")
        logger.debug(f"Plaid client_id: {self.client_id[:10]}... (truncated)")
        logger.debug(f"Plaid secret: {'*' * len(self.secret) if self.secret else 'EMPTY'}")
    
    def _validate_configuration(self):
        """Validate Plaid configuration and raise errors for invalid setup"""
        if not self.client_id or not self.secret:
            logger.error("Plaid credentials are missing. Set PLAID_CLIENT_ID and PLAID_SECRET environment variables.")
            raise Exception("Plaid credentials not configured. Check environment variables.")
        
        # Check for placeholder values (but allow the specific sandbox credentials that were working)
        placeholder_values = [
            "your_plaid_client_id", 
            "your_plaid_secret"
        ]
        
        if self.client_id in placeholder_values or self.secret in placeholder_values:
            logger.error("Plaid credentials are using placeholder values. Please set valid credentials.")
            raise Exception("Invalid Plaid credentials. Please configure valid client_id and secret.")
        
        # Validate environment
        valid_envs = ['sandbox', 'development', 'production']
        if self.environment not in valid_envs:
            logger.warning(f"Invalid Plaid environment '{self.environment}'. Falling back to 'sandbox'.")
            self.environment = 'sandbox'
    
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
    
    async def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """Exchange public token for access token"""
        if not self.enabled:
            return self._disabled_response()
        
        try:
            exchange_request = {
                'public_token': public_token
            }
            
            result = await self._make_request('item/public_token/exchange', exchange_request)
            access_token = result.get('access_token')
            item_id = result.get('item_id')
            
            if not access_token:
                raise Exception("No access token received from Plaid")
            
            return {
                'success': True,
                'access_token': access_token,
                'item_id': item_id
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange public token: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to exchange public token'
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
    
    async def fetch_account_balances(self, access_token: str) -> Dict[str, Any]:
        """Fetch account balances from Plaid"""
        try:
            result = await self._make_request('accounts/balance/get', {
                'access_token': access_token
            })
            return {
                'success': True,
                'accounts': result.get('accounts', [])
            }
        except Exception as e:
            logger.error(f"Failed to fetch account balances: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def fetch_transactions(self, access_token: str, start_date: str, end_date: str,
                               account_ids: Optional[list] = None) -> Dict[str, Any]:
        """Fetch transactions from Plaid"""
        try:
            request_data = {
                'access_token': access_token,
                'start_date': start_date,
                'end_date': end_date
            }
            
            # Move account_ids into options object as per Plaid API requirements
            if account_ids:
                request_data['options'] = {
                    'account_ids': account_ids
                }
            
            result = await self._make_request('transactions/get', request_data)
            
            return {
                'success': True,
                'transactions': result.get('transactions', []),
                'accounts': result.get('accounts', []),
                'total_transactions': result.get('total_transactions', 0),
                'request_id': result.get('request_id')
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def fetch_recurring_transactions(self, access_token: str) -> Dict[str, Any]:
        """Fetch recurring transactions from Plaid"""
        try:
            result = await self._make_request('transactions/recurring/get', {
                'access_token': access_token
            })
            
            return {
                'success': True,
                'inflow_streams': result.get('inflow_streams', []),
                'outflow_streams': result.get('outflow_streams', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch recurring transactions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_connection_status(self, access_token: str) -> Dict[str, Any]:
        """Get connection status for a Plaid item"""
        try:
            result = await self._make_request('item/get', {
                'access_token': access_token
            })
            
            item = result.get('item', {})
            error = item.get('error')
            
            return {
                'success': True,
                'status': 'healthy' if not error else 'error',
                'error': error,
                'last_updated': item.get('update_type'),
                'available_products': item.get('available_products', []),
                'billed_products': item.get('billed_products', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Plaid API"""
        if not self.enabled:
            raise Exception("Plaid is disabled")
        
        # Add authentication to request
        data.update({
            'client_id': self.client_id,
            'secret': self.secret
        })
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'PLAID-CLIENT-NAME': 'Finance Tracker'
        }
        
        try:
            # Debug logging to understand what's being sent
            logger.debug(f"Plaid API request to {url}")
            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Request data keys: {list(data.keys())}")
            logger.debug(f"Has client_id: {'client_id' in data}")
            logger.debug(f"Has secret: {'secret' in data}")
            
            # Run the request in a thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=data, headers=headers, timeout=30)
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('error_message', error_detail)
                except:
                    pass
                raise Exception(f"Plaid API error ({response.status_code}): {error_detail}")
            
            result = response.json()
            logger.debug(f"Plaid API call to {endpoint} successful")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Plaid API timeout for endpoint: {endpoint}")
            raise Exception("Plaid service timeout")
        except requests.exceptions.ConnectionError:
            logger.error(f"Plaid API connection error for endpoint: {endpoint}")
            raise Exception("Unable to connect to Plaid service")
        except Exception as e:
            logger.error(f"Plaid API request failed for {endpoint}: {e}")
            raise
    
    def _disabled_response(self) -> Dict[str, Any]:
        """Standard response when Plaid is disabled"""
        return {
            'success': False,
            'error': 'Plaid integration is disabled',
            'message': 'Bank connections are currently unavailable'
        }


# Provider function with lazy caching
_plaid_client_service_instance = None

def get_plaid_client_service() -> PlaidClientService:
    """Get the global PlaidClientService instance with lazy initialization"""
    global _plaid_client_service_instance
    if _plaid_client_service_instance is None:
        _plaid_client_service_instance = PlaidClientService()
    return _plaid_client_service_instance