from email.policy import default
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import csv
from io import StringIO
from datetime import datetime, date
import asyncio
import logging

from app.core.exceptions import DataIntegrityError, BusinessLogicError, ValidationError

from app.database import get_db
from app.dependencies import get_transaction_service, get_websocket_manager_dep, get_owned_transaction
from app.services.transaction_service import TransactionService
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilter,
    TransactionPagination,
    TransactionListResponse,
    TransactionBulkDeleteRequest
)
from app.auth.dependencies import get_current_user, get_db_with_user_context
from app.models.user import User
from app.models.transaction import Transaction

# Singleton pattern for the websocket manager and logger

logger = logging.getLogger(__name__)



router = APIRouter(tags=["transactions"])

@router.post("", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    # This could be achieved by setting preferences think that later 
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    try:
        new_transaction = await TransactionService.create_transaction(db, transaction, current_user.id, current_user)
    except SQLAlchemyError as e:
        logger.error(f"Database error creating transaction: {str(e)}")
        raise DataIntegrityError("Failed to create transaction due to database error")
    except Exception as e:
        logger.error(f"Unexpected error creating transaction: {str(e)}", exc_info=True)
        raise BusinessLogicError("An error occurred while creating transaction")

    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                # Use standardized message type expected by frontend
                "type": "new_transaction",
                "payload": _serialize_transaction(new_transaction)
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")

    # Create persistent notification
    if notify:
        try:
            amount_display = abs(new_transaction.amount_cents) / 100.0
            transaction_type = "income" if new_transaction.amount_cents > 0 else "expense"
            
            await NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                type=NotificationType.TRANSACTION_ALERT,
                title=f"New {transaction_type.title()} Added",
                message=f"${amount_display:.2f} - {new_transaction.description or 'No description'}",
                action_url=f"/transactions?id={new_transaction.id}",
                metadata={
                    "transaction_id": str(new_transaction.id),
                    "amount_cents": new_transaction.amount_cents,
                    "transaction_type": transaction_type
                }
            )
        except Exception as e:
            logger.warning(f"Error creating transaction notification: {str(e)}")

    return new_transaction

@router.get("/histogram", response_model=dict)
def get_transaction_histogram(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    account_id: Optional[str] = Query(None, description="Account ID filter"),
    amount_min: Optional[float] = Query(None, description="Minimum amount filter (in dollars)"),
    amount_max: Optional[float] = Query(None, description="Maximum amount filter (in dollars)"),
    bins: int = Query(10, ge=5, le=50, description="Number of histogram bins"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get histogram data for transaction amounts"""
    return TransactionService.get_transaction_histogram(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        account_id=account_id,
        amount_min=amount_min,
        amount_max=amount_max,
        bins=bins
    )

from fastapi import Request as _Request
from app.core.rate_limit import limiter as _limiter
from app.config import settings as _settings


@router.get("/export")
@_limiter.limit("5/minute")
async def export_transactions(
    request: _Request,
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    category_id: Optional[str] = Query(None, description="Category ID filter"),
    transaction_type: Optional[str] = Query(None, description="Transaction type filter (income/expense)"),
    max_rows: Optional[int] = Query(None, ge=1, description="Optional row cap (clamped by EXPORT_MAX_ROWS)"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Export transactions in CSV/JSON. Streamed; rate-limited to 5/min;
    bounded by `EXPORT_MAX_ROWS` to mitigate DoS (BE-SEC-009)."""
    from fastapi.responses import StreamingResponse
    import json
    import csv
    import io

    hard_cap = int(getattr(_settings, "EXPORT_MAX_ROWS", 50_000) or 50_000)
    row_cap = min(max_rows, hard_cap) if max_rows else hard_cap
    
    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        transaction_type=transaction_type
    )
    
    def format_transaction_for_export(transaction):
        """Helper function to format a transaction for export"""
        amount_dollars = transaction.amount_cents / 100
        transaction_type = 'expense' if transaction.amount_cents < 0 else 'income'
        return {
            'id': str(transaction.id),
            'amount': abs(amount_dollars),
            'category': getattr(transaction.category, 'name', '') if transaction.category else '',
            'description': transaction.description or '',
            'transaction_date': transaction.transaction_date.strftime('%Y-%m-%d'),
            'transaction_type': transaction_type,
            'created_at': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    if format == "csv":
        def generate_csv():
            """Generator function for CSV streaming"""
            # Create in-memory buffer for CSV header
            output = io.StringIO()
            fieldnames = ['id', 'amount', 'category', 'description', 'transaction_date', 'transaction_type', 'created_at', 'updated_at']
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            # Write header
            writer.writeheader()
            yield output.getvalue()

            emitted = 0
            # Stream transactions in chunks
            for transaction_chunk in TransactionService.stream_transactions_for_export(db, current_user.id, filters):
                if emitted >= row_cap:
                    break
                # Clear buffer for next chunk
                output.seek(0)
                output.truncate(0)

                # Write chunk to buffer (respect row_cap)
                for transaction in transaction_chunk:
                    if emitted >= row_cap:
                        break
                    formatted_transaction = format_transaction_for_export(transaction)
                    # Remove updated_at for CSV to match original format
                    formatted_transaction.pop('updated_at')
                    writer.writerow(formatted_transaction)
                    emitted += 1

                # Yield chunk content
                yield output.getvalue()
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"}
        )
    
    else:  # json format
        def generate_json():
            """Generator function for JSON streaming"""
            yield "["  # Start JSON array
            first_item = True
            emitted = 0

            # Stream transactions in chunks
            for transaction_chunk in TransactionService.stream_transactions_for_export(db, current_user.id, filters):
                if emitted >= row_cap:
                    break
                for transaction in transaction_chunk:
                    if emitted >= row_cap:
                        break
                    emitted += 1
                    formatted_transaction = format_transaction_for_export(transaction)
                    # Update date formatting for JSON
                    formatted_transaction['transaction_date'] = transaction.transaction_date.isoformat()
                    formatted_transaction['created_at'] = transaction.created_at.isoformat()
                    formatted_transaction['updated_at'] = transaction.updated_at.isoformat()
                    
                    # Add comma separator between items (except for first item)
                    if not first_item:
                        yield ","
                    else:
                        first_item = False
                    
                    # Yield formatted transaction
                    yield json.dumps(formatted_transaction, indent=2)
            
            yield "]"  # Close JSON array
        
        return StreamingResponse(
            generate_json(),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=transactions.json"}
        )

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction = Depends(get_owned_transaction)
):
    return transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_update: TransactionUpdate,
    notify: bool = Query(default=True, description="Send real-time notification"),
    transaction = Depends(get_owned_transaction),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    updated_transaction = await TransactionService.update_transaction(db, transaction, transaction_update)

    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                "type": "transaction_updated",
                "payload": _serialize_transaction(updated_transaction)
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")

    # Create persistent notification
    if notify:
        try:
            amount_display = abs(updated_transaction.amount_cents) / 100.0
            transaction_type = "income" if updated_transaction.amount_cents > 0 else "expense"
            
            await NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                type=NotificationType.TRANSACTION_ALERT,
                title="Transaction Updated",
                message=f"${amount_display:.2f} - {updated_transaction.description or 'No description'}",
                action_url=f"/transactions?id={updated_transaction.id}",
                metadata={
                    "transaction_id": str(updated_transaction.id),
                    "amount_cents": updated_transaction.amount_cents,
                    "transaction_type": transaction_type
                }
            )
        except Exception as e:
            logger.warning(f"Error creating transaction update notification: {str(e)}")

    return updated_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(
    notify: bool = Query(default=True, description="Send real-time notification"),
    transaction = Depends(get_owned_transaction),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    # Store transaction details for notification before deletion
    transaction_amount = transaction.amount_cents
    transaction_description = transaction.description
    transaction_id = transaction.id
    
    TransactionService.delete_transaction(db, transaction)

    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                "type": "transaction_deleted",
                "payload": {"id": transaction_id}
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")

    # Create persistent notification
    if notify:
        try:
            amount_display = abs(transaction_amount) / 100.0
            transaction_type = "income" if transaction_amount > 0 else "expense"
            
            await NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                type=NotificationType.TRANSACTION_ALERT,
                title="Transaction Deleted",
                message=f"Deleted {transaction_type}: ${amount_display:.2f} - {transaction_description or 'No description'}",
                action_url="/transactions",
                metadata={
                    "deleted_transaction_id": str(transaction_id),
                    "amount_cents": transaction_amount,
                    "transaction_type": transaction_type
                }
            )
        except Exception as e:
            logger.warning(f"Error creating transaction deletion notification: {str(e)}")

    return {"message": "Transaction deleted successfully"}

@router.get("")
def get_transactions(
    filters: TransactionFilter = Depends(),
    pagination: TransactionPagination = Depends(),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"[TransactionRoute] GET /transactions called for user {current_user.id}")
    logger.info(f"[TransactionRoute] Raw filters: {filters.model_dump()}")
    logger.info(f"[TransactionRoute] Pagination: offset={pagination.offset}, limit={pagination.limit}")
    
    # Check if grouping is requested
    if filters.group_by and filters.group_by != "none":
        logger.info(f"[TransactionRoute] Using grouped method with group_by={filters.group_by}")
        # Use the new grouped method - returns TransactionGroupedResponse
        return TransactionService.get_transactions_with_grouping(
            db, current_user.id, filters, pagination
        )
    else:
        logger.info("[TransactionRoute] Using flat method")
        # Use the original flat method
        transactions, total_count = TransactionService.get_transactions_with_filters(
            db, current_user.id, filters, pagination
        )
        
        # Calculate pagination values
        has_more = total_count > pagination.offset + len(transactions)
        
        response = TransactionListResponse(
            transactions=transactions,
            total=total_count,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=has_more
        )
        
        logger.info(f"[TransactionRoute] Returning response with {len(transactions)} transactions, total={total_count}, has_more={has_more}")
        return response

@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    if not file.filename.endswith('.csv'):
        raise ValidationError("Only CSV files are supported")

    # Get user's accounts and prioritize Plaid credit card for CSV imports
    from app.services.account_service import AccountService
    from app.schemas.account import AccountCreate
    account_service = AccountService()
    user_accounts = account_service.get_by_user(db, current_user.id)
    
    if not user_accounts:
        # Create a default account if user has none
        default_account = account_service.create_for_user(
            db,
            obj_in=AccountCreate(
                name="CSV Import Account",
                account_type="checking",
                balance_cents=0,
                user_id=current_user.id
            ),
            user_id=current_user.id
        )
        default_account_id = default_account.id
        logger.info(f"Created default CSV import account {default_account_id} for user {current_user.id}")
    else:
        # Prioritize Plaid-connected credit card accounts for CSV imports
        plaid_credit_cards = [acc for acc in user_accounts 
                             if acc.account_type == "credit_card" and acc.plaid_account_id is not None]
        
        if plaid_credit_cards:
            default_account_id = plaid_credit_cards[0].id
            logger.info(f"Using Plaid credit card account {default_account_id} for CSV import for user {current_user.id}")
        else:
            # Fallback to first available account
            default_account_id = user_accounts[0].id
            logger.info(f"Using fallback account {default_account_id} for CSV import for user {current_user.id}")

    content = await file.read()
    csv_content = StringIO(content.decode())
    csv_reader = csv.DictReader(csv_content)
    
    transactions = []
    errors = []
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is headers
        try:
            # Parse amount (convert dollars to cents)
            amount_dollars = float(row['amount'])
            amount_cents = int(amount_dollars * 100)
            
            # Parse transaction type and adjust amount sign
            transaction_type = row['transaction_type'].lower()
            if transaction_type == 'expense' and amount_cents > 0:
                amount_cents = -amount_cents  # Expenses should be negative
            
            # Parse date
            transaction_date = datetime.strptime(row['transaction_date'], "%Y-%m-%d").date()
            
            # Create transaction object
            transaction = TransactionCreate(
                account_id=default_account_id,
                amount_cents=amount_cents,
                description=row.get('description', ''),
                transaction_date=transaction_date,
                category_id=None  # Will be set by ML categorization
            )
            transactions.append(transaction)
        except (ValueError, KeyError) as e:
            errors.append(f"Row {row_num}: {str(e)}")
        except Exception as e:
            logger.error(f"CSV import error on row {row_num}: {str(e)}", exc_info=True)
            errors.append(f"Row {row_num}: Invalid data format")
    
    if errors:
        raise ValidationError(f"Invalid data in CSV rows: {'; '.join(errors)}")

    imported_transactions = TransactionService.import_transactions_from_csv(
        db, current_user.id, transactions
    )

    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                "type": "bulk_transactions_imported",
                "payload": {
                    # TODO: Large Imports: For very large CSV imports, consider sending progress updates
                    "count": len(imported_transactions),
                    "transactions": [_serialize_transaction(t) for t in imported_transactions]
                }
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")
    
    return {
        "message": f"Successfully imported {len(imported_transactions)} transactions",
        "imported_count": len(imported_transactions),
        "errors": errors,
        "transactions": [_serialize_transaction(t) for t in imported_transactions]
    }

@router.post("/bulk-delete")
async def bulk_delete_transactions(
    request: TransactionBulkDeleteRequest,
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    """Delete multiple transactions at once"""
    if not request.transaction_ids:
        raise ValidationError("No transaction IDs provided")
    
    try:
        # Use efficient bulk delete service method
        deleted_ids = TransactionService.bulk_delete_transactions(
            db, current_user.id, request.transaction_ids
        )
        deleted_count = len(deleted_ids)
    except SQLAlchemyError as e:
        logger.error(f"Database error during bulk delete operation: {str(e)}", exc_info=True)
        raise DataIntegrityError("Failed to delete transactions due to database error")
    except Exception as e:
        logger.error(f"Error during bulk delete operation: {str(e)}", exc_info=True)
        raise BusinessLogicError("An error occurred while deleting transactions")
    
    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                "type": "transactions_deleted",
                "payload": {"count": deleted_count, "deleted_ids": [str(uuid) for uuid in deleted_ids]}
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")

    # Create persistent notification
    if notify and deleted_count > 0:
        try:
            await NotificationService.create_notification(
                db=db,
                user_id=current_user.id,
                type=NotificationType.TRANSACTION_ALERT,
                title="Transactions Deleted",
                message=f"Successfully deleted {deleted_count} transaction{'s' if deleted_count != 1 else ''}",
                action_url="/transactions",
                metadata={
                    "deleted_count": deleted_count,
                    "deleted_ids": [str(uuid) for uuid in deleted_ids]
                }
            )
        except Exception as e:
            logger.warning(f"Error creating bulk deletion notification: {str(e)}")

    return {
        "message": f"Successfully deleted {deleted_count} transactions",
        "deleted_count": deleted_count
    }

@router.get("/search_transactions", response_model=dict)
async def search_transactions(
    q: str = Query(..., min_length=1, description="Search query"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    transaction_type: Optional[str] = Query(None, description="Transaction type filter"),
    limit: int = Query(25, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Advanced search for transactions with multiple filters"""
    filters = TransactionFilter(
        search_query=q,
        start_date=start_date,
        end_date=end_date,
        category=category,
        transaction_type=transaction_type
    )
    pagination = TransactionPagination(limit=limit, offset=offset)
    
    transactions, total_count = TransactionService.get_transactions_with_filters(
        db, current_user.id, filters, pagination
    )
    
    # Calculate pagination info
    has_more = total_count > pagination.offset + len(transactions)
    
    return {
        "items": transactions,
        "total": total_count,
        "limit": pagination.limit,
        "offset": pagination.offset,
        "has_more": has_more,
        "search_query": q
    }

@router.get("/categories", response_model=List[str])
def get_transaction_categories(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Get all unique transaction categories for the current user"""
    categories = db.query(Transaction.category).filter(
        Transaction.user_id == current_user.id
    ).distinct().all()
    return [category[0] for category in categories if category[0]]

def _serialize_transaction(transaction: Transaction) -> dict:
    """Serialize a Transaction model into a WS-friendly payload.

    Matches frontend TransactionPayload expectations (amount_cents, ids, names, ISO dates).
    """
    return {
        "id": str(transaction.id),
        "amount_cents": int(transaction.amount_cents),
        "description": transaction.description,
        "merchant": transaction.merchant,
        "category_id": str(transaction.category_id) if transaction.category_id else None,
        "category_name": getattr(transaction.category, 'name', None) if getattr(transaction, 'category', None) else None,
        "category_emoji": getattr(transaction.category, 'emoji', None) if getattr(transaction, 'category', None) else None,
        "account_id": str(transaction.account_id),
        "account_name": getattr(transaction.account, 'name', None) if getattr(transaction, 'account', None) else None,
        "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        "is_income": transaction.amount_cents > 0,
    }
