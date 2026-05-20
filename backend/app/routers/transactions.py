from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.models.transaction import Transaction
from sqlalchemy import or_

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("/recent")
def get_recent_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(Transaction).filter(
        or_(
            Transaction.sender_id == current_user.id,
            Transaction.receiver_id == current_user.id
        )
    ).order_by(Transaction.created_at.desc()).limit(20).all()

    return [
        {
            "id": str(tx.id),
            "reference": tx.reference,
            "amount": float(tx.amount),
            "currency": tx.currency,
            "transaction_type": tx.transaction_type,
            "status": tx.status,
            "description": tx.description,
            "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "sender_id": str(tx.sender_id) if tx.sender_id else None,
            "receiver_id": str(tx.receiver_id) if tx.receiver_id else None,
            "sender_account_number": tx.sender_account_number,
            "receiver_account_number": tx.receiver_account_number,
        }
        for tx in transactions
    ]