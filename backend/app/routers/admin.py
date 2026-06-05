from fastapi import APIRouter, Depends, HTTPException
import random
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.account import Account
from app.models.admin_transaction import AdminTransaction, AdminTransactionType, AdminTransferType
from app.models.cot_code import COTCode, CodeType
from app.models.notification import NotificationType
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.middleware.auth import get_current_user
from app.utils.hashing import hash_password, hash_pin
from app.utils.account_number import generate_account_number
from app.utils.account_number import generate_transaction_reference
from app.services.email_service import send_admin_credit_email, send_admin_debit_email
from app.services.notification_service import NotificationService
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
from typing import Optional
import secrets
import string

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def get_current_admin(current_user: User = Depends(get_current_user)):
    """Dependency to verify user is admin and not blocked."""
    if current_user.role != UserRole.admin and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    if current_user.status == UserStatus.blocked:
        raise HTTPException(status_code=403, detail="Your admin account has been blocked")
    return current_user


# Schemas
class UserCreateRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    transaction_pin: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "United States"
    initial_balance: Optional[float] = 0.0
    skip_email_verification: bool = False


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class UserPasswordResetRequest(BaseModel):
    new_password: str


class CreditUserRequest(BaseModel):
    amount: float
    sender_name: str
    bank_name: str
    transfer_type: str  # local or international
    description: Optional[str] = ""
    account_number: Optional[str] = None
    transaction_date: Optional[str] = None


class DebitUserRequest(BaseModel):
    amount: float
    description: str
    reason: str
    transaction_date: Optional[str] = None


class BlockUserRequest(BaseModel):
    reason: str


class GenerateCodeRequest(BaseModel):
    code_type: str  # cot or bop
    expires_in_hours: Optional[int] = 24
    user_email: Optional[str] = None


# Helper functions
def gen_random_code():
    """Generate a random COT/BOP code"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


# Endpoints

@router.get("/users")
def get_all_users(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all users with pagination and search"""
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))
        )
    
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for user in users:
        account = db.query(Account).filter(Account.user_id == user.id).first()
        result.append({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "account_number": account.account_number if account else None,
            "balance": float(account.balance) if account else 0.0,
            "role": user.role.value,
            "status": user.status.value,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        })
    
    return {
        "users": result,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.post("/users")
def create_user(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        country=data.country,
        role=UserRole.user,
        status=UserStatus.active,
        is_email_verified=data.skip_email_verification
    )

    # Set PIN if provided
    if data.transaction_pin:
        user.transaction_pin = hash_pin(data.transaction_pin)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create account
    account_number = generate_account_number(db)
    account = Account(
        user_id=user.id,
        account_number=account_number,
        balance=Decimal(str(data.initial_balance))
    )
    db.add(account)
    db.commit()
    
    return {
        "message": "User created successfully",
        "user_id": str(user.id),
        "account_number": account_number
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.phone is not None:
        user.phone = data.phone
    if data.address is not None:
        user.address = data.address
    if data.city is not None:
        user.city = data.city
    if data.state is not None:
        user.state = data.state
    if data.zip_code is not None:
        user.zip_code = data.zip_code
    if data.country is not None:
        user.country = data.country
    
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "User updated successfully"}


@router.post("/users/{user_id}/password")
def reset_user_password(
    user_id: str,
    data: UserPasswordResetRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Reset user password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/users/{user_id}/credit")
def credit_user(
    user_id: str,
    data: CreditUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Credit user account (manual transfer)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Parse transaction date if provided
    transaction_date = None
    if data.transaction_date:
        try:
            transaction_date = datetime.fromisoformat(data.transaction_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except:
            transaction_date = datetime.utcnow()
    else:
        transaction_date = datetime.utcnow()
    
    # Update balance
    account.balance += Decimal(str(data.amount))
    
    # Create admin transaction record
    reference = generate_transaction_reference()
    final_account_number = data.account_number or f"00{random.randint(10000000, 99999999)}"

    admin_transaction = AdminTransaction(
        admin_id=current_admin.id,
        user_id=user.id,
        transaction_type=AdminTransactionType.credit,
        amount=Decimal(str(data.amount)),
        sender_name=data.sender_name,
        bank_name=data.bank_name,
        transfer_type=AdminTransferType(data.transfer_type) if data.transfer_type in ["local", "international"] else None,
        description=data.description,
        account_number=final_account_number,
        transaction_date=transaction_date,
        reference=reference
    )
    db.add(admin_transaction)
    db.commit()
    
    # Create regular transaction record for user history
    transaction = Transaction(
        receiver_id=user.id,
        transaction_type=TransactionType.credit,
        amount=Decimal(str(data.amount)),
        description=data.description or f"Credit from {data.sender_name} ({data.bank_name})",
        reference=reference,
        status=TransactionStatus.completed,
        transaction_date=transaction_date,
        receiver_account_number=account.account_number,
        recipient_name=f"{user.first_name} {user.last_name}",
        sender_name=data.sender_name,
        recipient_bank=data.bank_name,
        recipient_account=final_account_number,
        created_by_admin=True,
        admin_id=current_admin.id
    )
    db.add(transaction)
    db.commit()
    
    # Create notification
    notification = NotificationService.create_notification(
        db,
        user.id,
        "Account Credited",
        f"Your account has been credited with {data.amount} from {data.sender_name}. Reference: {reference}",
        NotificationType.transaction,
        related_id=str(transaction.id),
        related_type="transaction",
        data={"amount": float(data.amount), "reference": reference},
        created_at=transaction_date
    )
    db.commit()
    
    # Send email
    try:
        send_admin_credit_email(
            to=user.email,
            first_name=user.first_name,
            amount=f"${data.amount:,.2f}",
            reference=reference,
            sender_name=data.sender_name,
            bank_name=data.bank_name,
            transaction_date=transaction_date.strftime("%B %d, %Y at %I:%M %p UTC") if transaction_date else datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC"),
            description=data.description or "Admin credit",
            new_balance=f"${account.balance:,.2f}"
        )
    except Exception:
        pass  # Never block transaction due to email failure
    
    return {
        "message": "User credited successfully",
        "transaction_id": str(admin_transaction.id),
        "reference": reference,
        "new_balance": float(account.balance)
    }


@router.post("/users/{user_id}/debit")
def debit_user(
    user_id: str,
    data: DebitUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Debit user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check sufficient balance
    if account.balance < Decimal(str(data.amount)):
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Update balance
    account.balance -= Decimal(str(data.amount))
    
    # Create admin transaction record
    reference = generate_transaction_reference()
    admin_transaction = AdminTransaction(
        admin_id=current_admin.id,
        user_id=user.id,
        transaction_type=AdminTransactionType.debit,
        amount=Decimal(str(data.amount)),
        description=data.description,
        reference=reference
    )
    db.add(admin_transaction)
    db.commit()
    
    # Parse transaction date if provided
    debit_transaction_date = datetime.utcnow()
    if hasattr(data, 'transaction_date') and data.transaction_date:
        try:
            debit_transaction_date = datetime.fromisoformat(data.transaction_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            debit_transaction_date = datetime.utcnow()

    # Create regular transaction record for user history
    transaction = Transaction(
        sender_id=user.id,
        transaction_type=TransactionType.debit,
        amount=Decimal(str(data.amount)),
        description=data.description or f"Debit: {data.reason}",
        reference=reference,
        status=TransactionStatus.completed,
        transaction_date=debit_transaction_date,
        sender_account_number=account.account_number,
        created_by_admin=True,
        admin_id=current_admin.id
    )
    db.add(transaction)
    db.commit()
    
    # Create notification
    notification = NotificationService.create_notification(
        db,
        user.id,
        "Account Debited",
        f"Your account has been debited with {data.amount}. Reason: {data.reason}. Reference: {reference}",
        NotificationType.transaction,
        related_id=str(transaction.id),
        related_type="transaction",
        data={"amount": float(data.amount), "reference": reference},
        created_at=debit_transaction_date
    )
    db.commit()
    
    # Send email
    try:
        send_admin_debit_email(
            to=user.email,
            first_name=user.first_name,
            amount=f"${data.amount:,.2f}",
            reference=reference,
            reason=data.reason,
            transaction_date=datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC"),
            description=data.description,
            new_balance=f"${account.balance:,.2f}"
        )
    except Exception:
        pass  # Never block transaction due to email failure
    
    return {
        "message": "User debited successfully",
        "transaction_id": str(admin_transaction.id),
        "reference": reference,
        "new_balance": float(account.balance)
    }


@router.post("/users/{user_id}/block")
def block_user(
    user_id: str,
    data: BlockUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Block user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent blocking admins
    if user.role == UserRole.admin or user.role == UserRole.superadmin:
        raise HTTPException(status_code=400, detail="Cannot block admin accounts")
    
    # Update user status
    user.status = UserStatus.blocked
    user.blocked_at = datetime.utcnow()
    user.blocked_reason = data.reason
    
    # Update account status
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if account:
        account.blocked_at = datetime.utcnow()
        account.blocked_reason = data.reason
    
    db.commit()

    # Notify blocked user — capture user_id before session expires the object
    blocked_user_id = user.id
    from app.models.notification import NotificationType as NT
    NotificationService.create_notification(
        db,
        blocked_user_id,
        "Account Blocked",
        f"Your account has been blocked. Reason: {data.reason}. Please contact support@arcteronbank for assistance.",
        NT.warning
    )
    db.commit()
    
    return {"message": "User blocked successfully"}


@router.post("/users/{user_id}/unblock")
def unblock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Unblock user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user status
    user.status = UserStatus.active
    user.blocked_at = None
    user.blocked_reason = None
    
    # Update account status
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if account:
        account.blocked_at = None
        account.blocked_reason = None
    
    db.commit()
    
    return {"message": "User unblocked successfully"}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Activate a pending user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != UserStatus.pending:
        raise HTTPException(status_code=400, detail="User is not in pending status")

    user.status = UserStatus.active
    db.commit()

    # Capture user_id before session expires the object
    activated_user_id = user.id
    from app.models.notification import NotificationType as NT
    from app.services.notification_service import NotificationService
    NotificationService.create_notification(
        db,
        activated_user_id,
        "Account Activated",
        "Your account has been activated by an administrator. You can now log in and access all features.",
        NT.system
    )
    db.commit()

    return {"message": "User activated successfully"}


@router.get("/transactions")
def get_admin_transactions(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all admin transactions"""
    transactions = db.query(AdminTransaction).order_by(AdminTransaction.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for tx in transactions:
        user = db.query(User).filter(User.id == tx.user_id).first()
        admin = db.query(User).filter(User.id == tx.admin_id).first()
        
        result.append({
            "id": str(tx.id),
            "reference": tx.reference,
            "transaction_type": tx.transaction_type,
            "amount": float(tx.amount),
            "transaction_date": tx.transaction_date,
            "created_at": tx.created_at,
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "admin_name": f"{admin.first_name} {admin.last_name}" if admin else "Unknown",
            "description": tx.description,
            "sender_name": tx.sender_name,
            "bank_name": tx.bank_name
        })
    
    return {
        "transactions": result,
        "page": page,
        "per_page": per_page,
        "total": len(result)
    }


@router.post("/users/{user_id}/promote")
def promote_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Promote user to admin"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == UserRole.admin or user.role == UserRole.superadmin:
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    user.role = UserRole.admin
    db.commit()
    
    return {"message": "User promoted to admin successfully"}


@router.post("/users/{user_id}/demote")
def demote_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Demote admin to regular user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role != UserRole.admin:
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    # Prevent demoting self
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    
    user.role = UserRole.user
    db.commit()
    
    return {"message": "User demoted successfully"}


@router.post("/users/{user_id}/cot-code")
def generate_cot_code(
    user_id: str,
    data: GenerateCodeRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Generate COT/BOP code for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    code_type = CodeType.cot if data.code_type.lower() == "cot" else CodeType.bop
    
    # Generate code
    code = gen_random_code()
    expires_at = datetime.utcnow() + timedelta(hours=data.expires_in_hours)
    
    # Create code record
    cot_code = COTCode(
        user_id=user.id,
        generated_by_admin_id=current_admin.id,
        code_type=code_type,
        code=code,
        expires_at=expires_at
    )
    db.add(cot_code)
    db.commit()

    # Capture user details before session expires the object
    cot_user_id = user.id  # capture before commit
    cot_user_email = user.email
    cot_user_first_name = user.first_name

    # Send email to user with the code
    try:
        from app.services.email_service import send_cot_bop_code_email
        send_cot_bop_code_email(
            to=cot_user_email,
            first_name=cot_user_first_name,
            code_type=data.code_type.upper(),
            code=code,
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M UTC")
        )
    except Exception:
        pass  # Never block code generation because email failed

    # Send in-app notification
    from app.models.notification import NotificationType as NT
    from app.services.notification_service import NotificationService
    NotificationService.create_notification(
        db,
        cot_user_id,
        f"{data.code_type.upper()} Code Generated",
        f"Your {data.code_type.upper()} authorization code is: {code}. It expires at {expires_at.strftime('%Y-%m-%d %H:%M UTC')}. Use it when prompted during your transfer.",
        NT.system
    )
    db.commit()

    return {
        "message": f"{data.code_type.upper()} code generated successfully",
        "code": code,
        "expires_at": expires_at.isoformat()
    }





@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a user and all related records"""
    from app.models.notification import Notification
    from app.models.transaction import Transaction
    from app.models.cot_code import COTCode
    from app.models.admin_transaction import AdminTransaction

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    uid = user.id  # capture before session expires it

    # 1. Delete notifications
    db.query(Notification).filter(Notification.user_id == uid).delete(synchronize_session=False)

    # 2. Delete COT codes
    db.query(COTCode).filter(COTCode.user_id == uid).delete(synchronize_session=False)

    # 3. AdminTransactions: delete where user is the subject, null out where user was the admin
    db.query(AdminTransaction).filter(AdminTransaction.user_id == uid).delete(synchronize_session=False)
    db.query(AdminTransaction).filter(AdminTransaction.admin_id == uid).update(
        {"admin_id": None}, synchronize_session=False
    )

    # 4. Null out transaction references (preserve financial history)
    db.query(Transaction).filter(Transaction.sender_id == uid).update(
        {"sender_id": None}, synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.receiver_id == uid).update(
        {"receiver_id": None}, synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.admin_id == uid).update(
        {"admin_id": None}, synchronize_session=False
    )

    # 5. Delete account
    account = db.query(Account).filter(Account.user_id == uid).first()
    if account:
        db.delete(account)

    # 6. Delete user
    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/codes/generate")
def generate_code_by_email(
    data: GenerateCodeRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Generate COT/BOP code for user by email"""
    user = db.query(User).filter(User.email == data.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found with that email")

    code_type = CodeType.cot if data.code_type.lower() == "cot" else CodeType.bop
    code = gen_random_code()
    expires_at = datetime.utcnow() + timedelta(hours=data.expires_in_hours)

    cot_code = COTCode(
        user_id=user.id,
        generated_by_admin_id=current_admin.id,
        code_type=code_type,
        code=code,
        expires_at=expires_at
    )
    db.add(cot_code)
    db.commit()

    # Capture user details before session expires the object
    email_user_id = user.id  # capture before commit
    email_user_email = user.email
    email_user_first_name = user.first_name

    try:
        from app.services.email_service import send_cot_bop_code_email
        send_cot_bop_code_email(
            to=email_user_email,
            first_name=email_user_first_name,
            code_type=data.code_type.upper(),
            code=code,
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M UTC")
        )
    except Exception:
        pass

    from app.models.notification import NotificationType as NT
    from app.services.notification_service import NotificationService
    NotificationService.create_notification(
        db, email_user_id,
        f"{data.code_type.upper()} Code Generated",
        f"Your {data.code_type.upper()} authorization code is: {code}. Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}.",
        NT.system
    )
    db.commit()

    return {
        "message": f"{data.code_type.upper()} code generated successfully",
        "code": code,
        "expires_at": expires_at.isoformat()
    }

@router.get("/codes")
def get_all_codes(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all COT/BOP codes"""
    codes = db.query(COTCode).order_by(COTCode.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    result = []
    for code in codes:
        user = db.query(User).filter(User.id == code.user_id).first()
        admin = db.query(User).filter(User.id == code.generated_by_admin_id).first()
        
        result.append({
            "id": str(code.id),
            "code": code.code,
            "code_type": code.code_type.value,
            "is_used": code.is_used,
            "expires_at": code.expires_at.isoformat() if code.expires_at else None,
            "created_at": code.created_at.isoformat() if code.created_at else None,
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "admin_name": f"{admin.first_name} {admin.last_name}" if admin else "Unknown"
        })
    
    return {
        "codes": result,
        "page": page,
        "per_page": per_page,
        "total": len(result)
    }


@router.get("/users/{user_id}/codes")
def get_user_codes(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all codes for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    codes = db.query(COTCode).filter(COTCode.user_id == user_id).all()
    
    result = []
    for code in codes:
        result.append({
            "id": str(code.id),
            "code_type": code.code_type.value,
            "code": code.code,
            "expires_at": code.expires_at.isoformat(),
            "is_used": code.is_used,
            "used_at": code.used_at.isoformat() if code.used_at else None,
            "created_at": code.created_at.isoformat()
        })
    
    return {"codes": result}
