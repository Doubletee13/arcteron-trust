from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from app.models.user import User, UserRole, UserStatus
from app.models.account import Account
from app.models.card import Card
from app.models.transaction import Transaction
from app.models.notification import Notification
from app.models.cot_code import COTCode
from app.models.code import TransactionCode
from app.models.admin_transaction import AdminTransaction
from app.models.audit_log import AuditLog
from app.schemas.user import (
    RegisterStep1,
    RegisterStep2,
    RegisterStep3,
    RegisterStep4,
    LoginRequest,
    user_to_response,
)
from app.utils.hashing import hash_password, verify_password, hash_pin
from app.utils.jwt import create_access_token
from app.utils.account_number import generate_account_number
from app.utils.tokens import generate_verification_token
from app.utils.currency import get_currency_for_country
import traceback
import re
import uuid


def _purge_users(user_ids: list, db: Session):
    """Delete users and ALL their FK-constrained child records in correct order."""
    if not user_ids:
        return
    # 1. Cards (reference accounts)
    account_ids = [a.id for a in db.query(Account).filter(Account.user_id.in_(user_ids)).all()]
    if account_ids:
        db.query(Card).filter(Card.account_id.in_(account_ids)).delete(synchronize_session=False)
    # 2. COT Codes
    db.query(COTCode).filter(
        (COTCode.user_id.in_(user_ids)) | (COTCode.generated_by_admin_id.in_(user_ids))
    ).delete(synchronize_session=False)
    # 3. Transaction Codes
    db.query(TransactionCode).filter(
        (TransactionCode.assigned_to_user_id.in_(user_ids)) | (TransactionCode.generated_by_admin_id.in_(user_ids))
    ).delete(synchronize_session=False)
    # 4. Notifications
    db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
    # 5. Admin Transactions
    db.query(AdminTransaction).filter(
        (AdminTransaction.admin_id.in_(user_ids)) | (AdminTransaction.user_id.in_(user_ids))
    ).delete(synchronize_session=False)
    # 6. Audit Logs
    db.query(AuditLog).filter(AuditLog.admin_id.in_(user_ids)).delete(synchronize_session=False)
    # 7. Transactions
    db.query(Transaction).filter(
        (Transaction.sender_id.in_(user_ids)) | (Transaction.receiver_id.in_(user_ids)) | (Transaction.admin_id.in_(user_ids))
    ).delete(synchronize_session=False)
    # 8. Accounts
    db.query(Account).filter(Account.user_id.in_(user_ids)).delete(synchronize_session=False)
    # 9. Users
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


def register_step1(data: RegisterStep1, db: Session) -> User:
    import datetime as dt
    cutoff = datetime.utcnow() - dt.timedelta(minutes=10)

    # 1. Prune abandoned registrations older than 10 minutes (ONLY regular users, never admins)
    abandoned_ids = [
        u.id for u in db.query(User).filter(
            User.role == UserRole.user,
            User.has_accepted_terms == False,
            User.created_at < cutoff
        ).all()
    ]
    if abandoned_ids:
        _purge_users(abandoned_ids, db)

    # 2. Check if username already exists
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        is_temp = existing_user.email.startswith("temp_reg_")
        is_abandoned = not existing_user.has_accepted_terms and \
            (datetime.utcnow() - existing_user.created_at).total_seconds() > 600

        if is_temp or is_abandoned:
            _purge_users([existing_user.id], db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Generate a temporary unique dummy email and dummy password to satisfy NOT NULL constraints
    dummy_email = f"temp_reg_{uuid.uuid4()}@arcterontrust.com"
    dummy_hash = hash_password(str(uuid.uuid4()))

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        username=data.username,
        email=dummy_email,
        phone=None,
        hashed_password=dummy_hash,
        role=UserRole.user,
        status=UserStatus.pending,
        is_kyc_complete=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def register_step2(user_id: str, data: RegisterStep2, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Helper: is a conflicting record just an abandoned signup?
    def is_abandonable(conflicting: User) -> bool:
        return (
            not conflicting.has_accepted_terms and
            (datetime.utcnow() - conflicting.created_at).total_seconds() > 600
        )

    # Check if email is already taken by a real (completed) user
    email_conflict = db.query(User).filter(User.email == data.email, User.id != user.id).first()
    if email_conflict:
        if is_abandonable(email_conflict):
            db.query(Account).filter(Account.user_id == email_conflict.id).delete(synchronize_session=False)
            db.query(User).filter(User.id == email_conflict.id).delete(synchronize_session=False)
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Check if phone is already taken by a real (completed) user
    phone_conflict = db.query(User).filter(User.phone == data.phone, User.id != user.id).first()
    if phone_conflict:
        if is_abandonable(phone_conflict):
            db.query(Account).filter(Account.user_id == phone_conflict.id).delete(synchronize_session=False)
            db.query(User).filter(User.id == phone_conflict.id).delete(synchronize_session=False)
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    user.email = data.email
    user.phone = data.phone
    user.country = data.country

    db.commit()
    db.refresh(user)
    return user


def register_step3(user_id: str, data: RegisterStep3, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.transaction_pin = hash_pin(data.pin)

    # Check if account already exists (prevents duplicate on retry)
    existing_account = db.query(Account).filter(Account.user_id == user.id).first()
    if not existing_account:
        account_number = generate_account_number(db)
        account = Account(
            user_id=user.id,
            account_number=account_number,
            routing_number="011400754" if user.country == "United States" else None,
            account_type=data.account_type,
            balance=0.00,
            currency=data.currency,
            swift_code=f"ARCT{data.currency}1",
            bank_name="Arcteron Trust"
        )
        db.add(account)
    else:
        existing_account.currency = data.currency
        existing_account.account_type = data.account_type
        existing_account.swift_code = f"ARCT{data.currency}1"
        existing_account.routing_number = "011400754" if user.country == "United States" else None

    db.commit()
    db.refresh(user)
    return user


def register_step4(user_id: str, data: RegisterStep4, db: Session) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.password)
    user.has_accepted_terms = data.accept_terms
    user.status = UserStatus.active
    user.is_kyc_complete = False

    db.commit()
    db.refresh(user)

    return {"message": "Registration complete. Please verify your email.", "user": user_to_response(user)}


def login_user(data: LoginRequest, db: Session) -> dict:
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check email verification
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your inbox or request a new verification link."
        )

    # Check if account is blocked — return rich detail so frontend can render the blocked UI
    if user.status == UserStatus.blocked:
        import json
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=json.dumps({
                "code": "account_blocked",
                "message": "Your account has been blocked. Please contact support.",
                "reason": user.blocked_reason or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "profile_photo": user.profile_photo or "",
            })
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Send login alert email
    try:
        from app.services.email_service import send_login_alert
        account_last_four = "0000"
        if user.account:
            account_last_four = user.account.account_number[-4:]
        send_login_alert(
            to=user.email,
            first_name=user.first_name,
            email=user.email,
            account_last_four=account_last_four
        )
    except Exception:
        pass  # Never block login because email failed

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return {"access_token": token, "token_type": "bearer", "user": user_to_response(user)}