from email.policy import default
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
import csv
from io import StringIO
from datetime import datetime, date
import asyncio
import logging

from ..database import get_db
from ..services.transaction_service import TransactionService
from ..schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionFilter,
    TransactionPagination
)
from app.auth.dependencies import get_current_user
from ..models.user import User
from ..models.transaction import Transaction
from ..websocket.manager import WebSocketManager

# Singleton pattern for the websocket manager and logger

logger = logging.getLogger(__name__)

manager = WebSocketManager()


router = APIRouter(tags=["transactions"])

@router.post("", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    # This could be achieved by setting preferences think that later 
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_transaction = await TransactionService.create_transaction(db, transaction, current_user.id)

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
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction = TransactionService.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction = TransactionService.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    updated_transaction = TransactionService.update_transaction(db, transaction, transaction_update)

    await manager.send_to_user(str(current_user.id), {
        "type": "transaction_updated",
        "payload": _serialize_transaction(updated_transaction)
    })

    return updated_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transaction = TransactionService.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    TransactionService.delete_transaction(db, transaction)

    await manager.send_to_user(str(current_user.id), {
        "type": "transaction_deleted",
        "payload": {"id": transaction_id}
    })

    return {"message": "Transaction deleted successfully"}

@router.get("", response_model=dict)
def get_transactions(
    filters: TransactionFilter = Depends(),
    pagination: TransactionPagination = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transactions, total_count = TransactionService.get_transactions_with_filters(
        db, current_user.id, filters, pagination
    )
    
    # Serialize transactions manually to match the frontend expectations
    serialized_transactions = []
    for transaction in transactions:
        serialized_transactions.append({
            "id": str(transaction.id),
            "account_id": str(transaction.account_id),
            "category_id": str(transaction.category_id) if transaction.category_id else None,
            "amount_cents": transaction.amount_cents,
            "amount": transaction.amount_cents / 100.0,  # For frontend compatibility
            "currency": transaction.currency,
            "description": transaction.description,
            "merchant": transaction.merchant,
            "transaction_date": transaction.transaction_date.isoformat(),
            "status": transaction.status,
            "is_recurring": transaction.is_recurring,
            "is_transfer": transaction.is_transfer,
            "notes": transaction.notes,
            "tags": transaction.tags or [],
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "transaction_type": "income" if transaction.amount_cents > 0 else "expense",
            "category": "Food & Dining"  # TODO: Fetch actual category name from relationship
        })
    
    return {
        "items": serialized_transactions,
        "total": total_count,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": (total_count + pagination.per_page - 1) // pagination.per_page
    }

@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    csv_content = StringIO(content.decode())
    csv_reader = csv.DictReader(csv_content)
    
    transactions = []
    for row in csv_reader:
        try:
            transaction = TransactionCreate(
                amount=float(row['amount']),
                category=row['category'],
                description=row.get('description'),
                transaction_date=datetime.strptime(row['transaction_date'], "%Y-%m-%d"),
                transaction_type=row['transaction_type']
            )
            transactions.append(transaction)
        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data in CSV: {str(e)}"
            )

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
        "imported_count": len(imported_transactions)
    }

@router.post("/bulk-delete")
async def bulk_delete_transactions(
    transaction_ids: List[UUID],
    notify: bool = Query(default=True, description="Send real-time notification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete multiple transactions at once"""
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    deleted_count = 0
    deleted_ids = []

    for transaction_id in transaction_ids:
        transaction = TransactionService.get_transaction(db, transaction_id, current_user.id)
        if transaction:
            TransactionService.delete_transaction(db, transaction)
            deleted_count += 1
            deleted_ids.append(transaction_id)
    
    if notify and manager.is_user_connected(str(current_user.id)):
        try:
            await manager.send_to_user(str(current_user.id), {
                "type": "transactions_deleted",
                "payload": {"count": deleted_count, "deleted_ids": deleted_ids}
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export transactions in CSV or JSON format"""
    from fastapi.responses import Response
    import json
    import io
    
    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        category=category
    )
    pagination = TransactionPagination(page=1, per_page=10000)  # Large number to get all
    
    transactions, _ = TransactionService.get_transactions_with_filters(
        db, current_user.id, filters, pagination
    )
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'amount', 'category', 'description', 'transaction_date', 'transaction_type', 'created_at'
        ])
        writer.writeheader()
        
        for transaction in transactions:
            writer.writerow({
                'id': transaction.id,
                'amount': transaction.amount,
                'category': transaction.category,
                'description': transaction.description or '',
                'transaction_date': transaction.transaction_date.strftime('%Y-%m-%d'),
                'transaction_type': transaction.transaction_type,
                'created_at': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"}
        )
    else:  # json
        data = []
        for transaction in transactions:
            data.append({
                'id': transaction.id,
                'amount': transaction.amount,
                'category': transaction.category,
                'description': transaction.description,
                'transaction_date': transaction.transaction_date.isoformat(),
                'transaction_type': transaction.transaction_type,
                'created_at': transaction.created_at.isoformat(),
                'updated_at': transaction.updated_at.isoformat()
            })
        
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=transactions.json"}
        )

@router.get("/analytics/stats")
def get_transaction_stats(
    start_date: Optional[date] = Query(None, description="Start date for stats period"),
    end_date: Optional[date] = Query(None, description="End date for stats period"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    search_query: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transaction summary statistics"""
    return TransactionService.get_transaction_summary(db, current_user.id, start_date, end_date, category_id, search_query)

@router.get("/analytics/dashboard")
def get_dashboard_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics period"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard analytics for the current user"""
    return TransactionService.get_dashboard_analytics(db, current_user.id, start_date, end_date)

@router.get("/analytics/trends")
def get_spending_trends(
    period: str = Query("monthly", pattern="^(weekly|monthly)$", description="Trend period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending trends over time"""
    return TransactionService.get_spending_trends(db, current_user.id, period) 

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