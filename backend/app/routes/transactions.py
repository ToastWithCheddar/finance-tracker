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

from ..database import get_db
from app.dependencies import get_transaction_service, get_websocket_manager_dep, get_owned_transaction
from ..services.transaction_service import TransactionService
from ..schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilter,
    TransactionPagination,
    TransactionListResponse
)
from app.auth.dependencies import get_current_user, get_db_with_user_context
from ..models.user import User
from ..models.transaction import Transaction

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
        new_transaction = await TransactionService.create_transaction(db, transaction, current_user.id)
    except SQLAlchemyError as e:
        logger.error(f"Database error creating transaction: {str(e)}")
        raise DataIntegrityError("Failed to create transaction due to database error")
    except Exception as e:
        logger.error(f"Unexpected error creating transaction: {str(e)}", exc_info=True)
        raise BusinessLogicError("An error occurred while creating transaction")

    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                # TODO "payload" : _serialize(new_transaction) write the function
                "type": "transaction_created",
                "payload": _serialize_transaction(new_transaction)
            })
        except Exception as e:
            logger.warning(f"Error sending real-time notification: {str(e)}")

    return new_transaction


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction = Depends(get_owned_transaction)
):
    return transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_update: TransactionUpdate,
    transaction = Depends(get_owned_transaction),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    updated_transaction = TransactionService.update_transaction(db, transaction, transaction_update)

    await manager.send_to_user(str(current_user.id), {
        "type": "transaction_updated",
        "payload": _serialize_transaction(updated_transaction)
    })

    return updated_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction = Depends(get_owned_transaction),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user),
    manager = Depends(get_websocket_manager_dep)
):
    TransactionService.delete_transaction(db, transaction)

    await manager.send_to_user(str(current_user.id), {
        "type": "transaction_deleted",
        "payload": {"id": transaction.id}
    })

    return {"message": "Transaction deleted successfully"}

@router.get("")
def get_transactions(
    filters: TransactionFilter = Depends(),
    pagination: TransactionPagination = Depends(),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    # Check if grouping is requested
    if filters.group_by and filters.group_by != "none":
        # Use the new grouped method - returns TransactionGroupedResponse
        return TransactionService.get_transactions_with_grouping(
            db, current_user.id, filters, pagination
        )
    else:
        # Use the original flat method
        transactions, total_count = TransactionService.get_transactions_with_filters(
            db, current_user.id, filters, pagination
        )
        
        # Calculate pagination values
        has_more = total_count > pagination.offset + len(transactions)
        
        return TransactionListResponse(
            transactions=transactions,
            total=total_count,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=has_more
        )

@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise ValidationError("Only CSV files are supported")

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
                account_id=UUID('00000000-0000-0000-0000-000000000000'),  # Default account, will be updated by service
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
                "type": "transactions_imported",
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
    transaction_ids: List[UUID],
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Delete multiple transactions at once"""
    if not transaction_ids:
        raise ValidationError("No transaction IDs provided")
    
    try:
        # Use efficient bulk delete service method
        deleted_ids = TransactionService.bulk_delete_transactions(
            db, current_user.id, transaction_ids
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
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
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
    pagination = TransactionPagination(page=page, per_page=per_page)
    
    transactions, total_count = TransactionService.get_transactions_with_filters(
        db, current_user.id, filters, pagination
    )
    
    return {
        "items": transactions,
        "total": total_count,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": (total_count + pagination.per_page - 1) // pagination.per_page,
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

@router.get("/export")
async def export_transactions(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
    """Export transactions in CSV or JSON format using streaming for efficient memory usage"""
    from fastapi.responses import StreamingResponse
    import json
    import csv
    import io
    
    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        category=category
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
            
            # Stream transactions in chunks
            for transaction_chunk in TransactionService.stream_transactions_for_export(db, current_user.id, filters):
                # Clear buffer for next chunk
                output.seek(0)
                output.truncate(0)
                
                # Write chunk to buffer
                for transaction in transaction_chunk:
                    formatted_transaction = format_transaction_for_export(transaction)
                    # Remove updated_at for CSV to match original format
                    formatted_transaction.pop('updated_at')
                    writer.writerow(formatted_transaction)
                
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
            
            # Stream transactions in chunks
            for transaction_chunk in TransactionService.stream_transactions_for_export(db, current_user.id, filters):
                for transaction in transaction_chunk:
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

def _serialize_transaction(transaction: Transaction) -> dict:
    """Serialize a transaction to a dictionary"""
    return {
        "id": transaction.id,
        "amount": transaction.amount,
        "category": transaction.category,
        "description": transaction.description,
        "transaction_date": transaction.transaction_date,
        "transaction_type": transaction.transaction_type,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at
    }