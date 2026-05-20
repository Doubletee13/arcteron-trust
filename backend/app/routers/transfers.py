from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.notification import Notification, NotificationType
from app.utils.hashing import verify_pin
from app.utils.account_number import generate_transaction_reference
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/api/transfers", tags=["Transfers"])


class LocalTransferRequest(BaseModel):
    recipient_account_number: str
    amount: float
    description: Optional[str] = None
    pin: str


class InternationalTransferRequest(BaseModel):
    recipient_name: str
    recipient_bank: str
    recipient_bank_address: Optional[str] = None
    recipient_account: str
    recipient_swift: str
    recipient_country: str
    recipient_routing: Optional[str] = None
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    pin: str
    cot_code: Optional[str] = None
    bop_code: Optional[str] = None


def create_notification(db, user_id, title, message, notif_type, transaction_id=None):
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notif_type,
        related_transaction_id=transaction_id
    )
    db.add(notif)


@router.post("/local")
def local_transfer(
    data: LocalTransferRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify PIN
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="Please set a transaction PIN before making transfers.")
    if not verify_pin(data.pin, current_user.transaction_pin):
        raise HTTPException(status_code=401, detail="Incorrect PIN. Transfer declined.")

    # Get sender account
    sender_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).first()

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    if sender_account.is_frozen:
        raise HTTPException(status_code=403, detail="Your account is frozen. Contact support.")

    # Get recipient account
    recipient_account = db.query(Account).filter(
        Account.account_number == data.recipient_account_number
    ).first()

    if not recipient_account:
        raise HTTPException(status_code=404, detail="Recipient account number not found in Arcteron Trust.")

    if recipient_account.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot transfer to your own account.")

    amount = Decimal(str(data.amount))

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero.")

    if amount > sender_account.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance.")

    # Minimum transfer
    if amount < Decimal("1.00"):
        raise HTTPException(status_code=400, detail="Minimum transfer amount is $1.00.")

    recipient_user = db.query(User).filter(
        User.id == recipient_account.user_id
    ).first()

    reference = generate_transaction_reference()

    # Snapshot balances
    sender_before = sender_account.balance
    receiver_before = recipient_account.balance

    # Execute transfer
    sender_account.balance -= amount
    recipient_account.balance += amount

    sender_after = sender_account.balance
    receiver_after = recipient_account.balance

    # Create transaction record
    transaction = Transaction(
        reference=reference,
        sender_id=current_user.id,
        receiver_id=recipient_account.user_id,
        amount=amount,
        currency="USD",
        transaction_type=TransactionType.local_transfer,
        status=TransactionStatus.completed,
        description=data.description or f"Transfer to {recipient_user.first_name} {recipient_user.last_name}",
        sender_account_number=sender_account.account_number,
        receiver_account_number=recipient_account.account_number,
        sender_balance_before=sender_before,
        sender_balance_after=sender_after,
        receiver_balance_before=receiver_before,
        receiver_balance_after=receiver_after,
        transaction_date=datetime.utcnow()
    )

    db.add(transaction)
    db.flush()

    # Notifications
    create_notification(
        db, current_user.id,
        "Transfer Sent",
        f"You sent {fmt_amount(amount)} to {recipient_user.first_name} {recipient_user.last_name}. Ref: {reference}",
        NotificationType.transaction,
        transaction.id
    )

    create_notification(
        db, recipient_account.user_id,
        "Money Received",
        f"You received {fmt_amount(amount)} from {current_user.first_name} {current_user.last_name}. Ref: {reference}",
        NotificationType.transaction,
        transaction.id
    )

    db.commit()
    db.refresh(transaction)

    return {
        "message": "Transfer successful.",
        "reference": reference,
        "amount": float(amount),
        "recipient": f"{recipient_user.first_name} {recipient_user.last_name}",
        "recipient_account": recipient_account.account_number,
        "new_balance": float(sender_after),
        "status": "completed",
        "transaction_date": transaction.transaction_date.isoformat()
    }


@router.post("/international")
def international_transfer(
    data: InternationalTransferRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify PIN
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="Please set a transaction PIN before making transfers.")
    if not verify_pin(data.pin, current_user.transaction_pin):
        raise HTTPException(status_code=401, detail="Incorrect PIN. Transfer declined.")

    # Get sender account
    sender_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).first()

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    if sender_account.is_frozen:
        raise HTTPException(status_code=403, detail="Your account is frozen. Contact support.")

    amount = Decimal(str(data.amount))

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero.")

    if amount < Decimal("10.00"):
        raise HTTPException(status_code=400, detail="Minimum international transfer is $10.00.")

    if amount > sender_account.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance.")

    # Check if COT/BOP required for large transfers
    if amount >= Decimal("10000.00"):
        if not data.cot_code and not data.bop_code:
            raise HTTPException(
                status_code=402,
                detail="Transfers of $10,000 or more require a COT or BOP code. Please contact your account manager."
            )

    reference = generate_transaction_reference()

    # Reserve balance (deduct but mark pending)
    sender_before = sender_account.balance
    sender_account.balance -= amount
    sender_after = sender_account.balance

    transaction = Transaction(
        reference=reference,
        sender_id=current_user.id,
        receiver_id=None,
        amount=amount,
        currency=data.currency,
        transaction_type=TransactionType.international_transfer,
        status=TransactionStatus.pending,
        description=data.description or f"International wire to {data.recipient_name}",
        recipient_name=data.recipient_name,
        recipient_bank=data.recipient_bank,
        recipient_bank_address=data.recipient_bank_address,
        recipient_account=data.recipient_account,
        recipient_swift=data.recipient_swift,
        recipient_country=data.recipient_country,
        recipient_routing=data.recipient_routing,
        sender_account_number=sender_account.account_number,
        sender_balance_before=sender_before,
        sender_balance_after=sender_after,
        requires_code=amount >= Decimal("10000.00"),
        code_type="COT" if data.cot_code else ("BOP" if data.bop_code else None),
        code_value=data.cot_code or data.bop_code,
        code_verified=bool(data.cot_code or data.bop_code),
        transaction_date=datetime.utcnow()
    )

    db.add(transaction)
    db.flush()

    create_notification(
        db, current_user.id,
        "International Transfer Initiated",
        f"Your wire of {fmt_amount(amount)} to {data.recipient_name} is pending review. Ref: {reference}",
        NotificationType.transaction,
        transaction.id
    )

    db.commit()
    db.refresh(transaction)

    return {
        "message": "International transfer submitted and is pending review.",
        "reference": reference,
        "amount": float(amount),
        "recipient": data.recipient_name,
        "recipient_bank": data.recipient_bank,
        "new_balance": float(sender_after),
        "status": "pending",
        "transaction_date": transaction.transaction_date.isoformat()
    }


@router.get("/verify-account/{account_number}")
def verify_account(
    account_number: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(
        Account.account_number == account_number
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if account.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="This is your own account.")

    user = db.query(User).filter(User.id == account.user_id).first()

    return {
        "account_number": account.account_number,
        "account_name": f"{user.first_name} {user.last_name}",
        "bank": "Arcteron Trust"
    }


def fmt_amount(amount: Decimal) -> str:
    return f"${amount:,.2f}"