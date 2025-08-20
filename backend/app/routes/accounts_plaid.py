"""
Plaid integration API endpoints for account connection and management.
Handles Plaid Link token creation, token exchange, and connection status.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.auth.dependencies import get_current_active_user, get_db_with_user_context
from app.dependencies import (
    get_account_service, 
    get_plaid_service, 
    get_websocket_manager_dep,
    get_owned_account
)
from app.models.user import User
from app.services.account_service import AccountService
from app.websocket.events import WebSocketEvent, EventType
from app.schemas.account import (
    PlaidLinkTokenResponse,
    PlaidExchangeTokenResponse,
    PlaidConnectionStatusResponse,
    PlaidOperationResponse
)
from app.core.exceptions import (
    PlaidIntegrationError,
    AuthenticationError,
    ValidationError,
    ExternalServiceError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plaid/link-token", response_model=PlaidLinkTokenResponse)
async def create_plaid_link_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service=Depends(get_plaid_service)
):
    """Create Plaid Link token for account connection"""
    try:
        result = await plaid_service.create_link_token(str(current_user.id))
        return PlaidLinkTokenResponse(
            link_token=result["link_token"],
            expiration=result.get("expiration"),
            request_id=result.get("request_id")
        )
    except Exception as e:
        logger.error(f"Failed to create link token for user {current_user.id}: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to create bank connection link")


@router.post("/plaid/exchange-token", response_model=PlaidExchangeTokenResponse)
async def exchange_plaid_token(
    public_token: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service=Depends(get_plaid_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Exchange Plaid public token for access token and create accounts"""
    try:
        # Debug logging to identify the issue
        logger.info(f"Exchange token request - User ID: {current_user.id if current_user else 'None'}")
        logger.info(f"Exchange token request - Public token: {public_token[:20]}..." if public_token else "No public token")
        
        if not current_user:
            raise AuthenticationError("Authentication required")
        
        result = await plaid_service.exchange_public_token(
            public_token, current_user.id, db
        )
        
        # Check if the service returned an error
        if not result.get('success', True):
            error_message = result.get('message', 'Failed to connect bank account')
            logger.error(f"Plaid service error for user {current_user.id}: {result.get('error', 'Unknown error')}")
            raise PlaidIntegrationError("Failed to connect bank account")
        
        # Ensure we have accounts in the result
        accounts = result.get('accounts', [])
        if not accounts:
            logger.warning(f"No accounts created for user {current_user.id}")
            raise ValidationError("No accounts were connected. Please try again.")
        
        # Send real-time notification
        try:
            event = WebSocketEvent(
                event_type=EventType.ACCOUNT_CONNECTED,
                data={
                    "message": f"Successfully connected {len(accounts)} accounts",
                    "accounts": [
                        {
                            "id": str(acc.id),
                            "name": acc.name,
                            "type": acc.account_type,
                            "balance": acc.balance_cents / 100
                        } for acc in accounts
                    ],
                    "institution": result.get('institution', {}).get('name', 'Bank')
                }
            )
            await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
            logger.info(f"Sent WebSocket notification for {len(accounts)} accounts")
        except Exception as ws_error:
            logger.warning(f"Failed to send WebSocket notification: {ws_error}")
            # Don't fail the whole process if WebSocket fails
        
        # Schedule initial sync
        try:
            background_tasks.add_task(
                _schedule_account_sync, 
                [str(acc.id) for acc in accounts], 
                db,
                plaid_service
            )
            logger.info(f"Scheduled background sync for {len(accounts)} accounts")
        except Exception as sync_error:
            logger.warning(f"Failed to schedule background sync: {sync_error}")
            # Don't fail the whole process if background task scheduling fails
        
        return PlaidExchangeTokenResponse(
            success=True,
            message=f"Successfully connected {len(accounts)} accounts",
            data={
                "accounts_created": len(accounts),
                "institution": result.get('institution', {}).get('name'),
                "accounts": [
                    {
                        "id": str(acc.id),
                        "name": acc.name,
                        "type": acc.account_type,
                        "balance": acc.balance_cents / 100,
                        "currency": acc.currency
                    } for acc in accounts
                ]
            }
        )
        
    except (PlaidIntegrationError, ValidationError, AuthenticationError):
        raise
    except Exception as e:
        logger.error(f"Failed to exchange token for user {current_user.id}: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to process bank connection")


@router.get("/connection-status", response_model=PlaidConnectionStatusResponse)
async def get_connection_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service=Depends(get_plaid_service)
):
    """Get Plaid connection status for user's accounts"""
    try:
        status_info = await plaid_service.get_connection_status(db, current_user.id)
        return PlaidConnectionStatusResponse(
            success=True,
            data=status_info
        )
    except Exception as e:
        logger.error(f"Failed to get connection status for user {current_user.id}: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to retrieve connection status")


@router.post("/plaid/update-mode", response_model=PlaidOperationResponse)
async def update_plaid_mode(
    account = Depends(get_owned_account),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service=Depends(get_plaid_service)
):
    """Update Plaid account to use update mode for authentication"""
    try:
        
        if not account.plaid_access_token:
            raise ValidationError("Account is not connected to Plaid")
        
        result = await plaid_service.create_link_token(
            str(current_user.id), 
            access_token=account.plaid_access_token
        )
        
        return PlaidOperationResponse(
            success=True,
            message="Update mode link token created successfully",
            account_id=account.id
        )
        
    except (ValidationError, PlaidIntegrationError):
        raise
    except Exception as e:
        logger.error(f"Failed to create update mode link token: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to create update link token")


@router.post("/plaid/disconnect", response_model=PlaidOperationResponse)
async def disconnect_plaid_account(
    account = Depends(get_owned_account),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db_with_user_context),
    plaid_service=Depends(get_plaid_service),
    websocket_manager=Depends(get_websocket_manager_dep)
):
    """Disconnect a Plaid account"""
    try:
        
        if not account.plaid_access_token:
            raise ValidationError("Account is not connected to Plaid")
        
        # Disconnect from Plaid
        result = await plaid_service.disconnect_account(db, account.id)
        
        # Send real-time notification
        try:
            event = WebSocketEvent(
                event_type=EventType.ACCOUNT_DISCONNECTED,
                data={
                    "account_id": str(account.id),
                    "account_name": account.name,
                    "message": "Account disconnected from bank"
                }
            )
            await websocket_manager.send_to_user(str(current_user.id), event.to_dict())
        except Exception as ws_error:
            logger.warning(f"Failed to send disconnect notification: {ws_error}")
        
        return PlaidOperationResponse(
            success=True,
            message="Account disconnected successfully",
            account_id=account.id
        )
        
    except (ValidationError, PlaidIntegrationError):
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect account {account.id}: {e}", exc_info=True)
        raise PlaidIntegrationError("Unable to disconnect account")


async def _schedule_account_sync(account_ids: List[str], db: Session, plaid_service):
    """Background task to schedule account sync"""
    try:
        await plaid_service.sync_account_balances(db, account_ids)
    except Exception as e:
        logger.error(f"Background sync failed: {e}")