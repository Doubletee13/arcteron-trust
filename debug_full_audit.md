# Full Code Audit Report

## Required Answers

### Q1: What happens immediately after a user clicks the email verification link?
**Answer:** The user lands on `verify-email.html`. The page exacts the `token` parameter from the URL and sends it in a POST request to `/api/auth/email-verification/confirm`. If successful, the UI updates to show a "Continue to Login" button. There is no automatic redirect. The user must click the button to be redirected.

**Exact redirect code** (from `frontend/pages/verify-email.html`):
```javascript
        function handleAction() {
            window.location.href = 'login.html';
        }
```

---

### Q2: Where in the code does the PIN prompt appear? What condition triggers showing the PIN page vs skipping it?
**Answer:** The PIN prompt logic is initiated globally for logged-in users via `Auth.requireVerifiedPin()` or similar gating functions at the top of protected pages (e.g., `set-pin.html` and `enter-pin.html`'s IIFE gate). 
If the user visits a protected page and `user.has_pin` is true, but `Auth.isPinSessionVerified()` returns false, they are redirected to `/frontend/pages/enter-pin.html`.

**Exact condition code** (from `frontend/pages/set-pin.html` / `enter-pin.html` gating):
```javascript
      if (user.has_pin === true && !Auth.isPinSessionVerified()) {
        window.location.href = '/frontend/pages/enter-pin.html';
      }
```
*Note: In `enter-pin.html`, if `user.has_pin === false`, it redirects to `set-pin.html`.*

---

### Q3: What is the user account status set to at registration (step1)? Is there any code that blocks a newly verified user from logging in? 
**Answer:** At registration (step1), the status is set to `UserStatus.active`. However, in `auth_service.py`'s `login_user` function, it explicitly checks `if not user.is_email_verified:`. If the email is verified, there is nothing blocking the login, as `status` is already `active` and `is_kyc_complete` is not checked for just logging in.

**Exact status field code** (from `backend/app/services/auth_service.py` `register_step1`):
```python
    user = User(
        first_name=data.first_name,
        # ...
        role=UserRole.user,
        status=UserStatus.active,
        is_kyc_complete=False
    )
```

---

### Q4: In the transfer flow, where is COT/BOP code checked? Is it checked before or after PIN?
**Answer:** The COT/BOP code is checked *after* the PIN is verified. In `backend/app/routers/transfers.py` under the `/international` endpoint, PIN verification happens first (lines 232-235). Then account existence, freezing, blocked status, and balance are checked. Finally, the COT/BOP code logic is checked for amounts >= $10,000.

**Exact transfer flow logic** (from `backend/app/routers/transfers.py`):
```python
    # Check if COT/BOP required for large transfers
    if amount >= Decimal("10000.00"):
        if not data.cot_code and not data.bop_code:
            raise HTTPException(
                status_code=402,
                detail="Transfers of $10,000 or more require a COT or BOP code. Please contact your account manager."
            )
```

---

### Q5: How is the PDF receipt generated? Which file and which function?
**Answer:** The PDF receipt is generated on the backend using the python `reportlab` library.
File: `backend/app/routers/transactions.py`
Function: `generate_receipt_pdf(tx, user, account, is_credit: bool, theme: str = 'dark', db: Session = None) -> bytes:`

**Code snippet** (truncated due to length, full logic in `transactions.py`):
```python
def generate_receipt_pdf(tx, user, account, is_credit: bool, theme: str = 'dark', db: Session = None) -> bytes:  # noqa: C901
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    # ... PDF construction logic ...
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
```

---

### Q6: Where are notifications rendered on the user notifications page?
**Answer:** In the frontend UI, notifications are fetched via `/api/notifications` and rendered dynamically. `frontend/assets/js/notifications-ui.js` contains a `renderNotifications(notifications)` or similar function (not explicitly found via grep, but it's loaded via JS on `notifications.html`).

**Note on Code context:** 
Looking at `frontend/assets/js/notifications-ui.js`, we see DOM manipulation that downloads a receipt inside the notifications UI when viewing transaction alerts (Line 303: `link.download = \`receipt-${txId}.pdf\`;`). The actual rendering loop creates DOM elements and appends them to the notification list container.

---

### Q7: Where are transactions rendered on the user transactions page?
**Answer:** Transactions are rendered via the `renderTransactions(txs)` javascript function in `frontend/pages/user/transactions.html` itself (and identically in the admin transactions page).

**Exact transaction list rendering code** (from `frontend/pages/user/transactions.html` line 1528+):
```javascript
            function renderTransactions(txs) {
                const tbody = document.getElementById('txBody');
                if (!txs || txs.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">
                                <div class="empty-state">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.5; margin-bottom: 12px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                                    <p>No transactions found</p>
                                </div>
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = txs.map(tx => {
                    // ... rendering html string ...
                }).join('');
            }
```

---

## Raw Source Code

### BACKEND 1: auth.py
File Path: `backend/app/routers/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import base64
import os
import httpx
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import (
    RegisterStep1,
    RegisterStep2,
    RegisterStep3,
    LoginRequest,
    TokenResponse,
    UserResponse,
    user_to_response,
    PasswordResetRequest,
    PasswordResetConfirm,
    SetPinRequest,
    PinResetRequest,
    PinResetConfirm,
    ProfileUpdateRequest,
    PhotoUploadRequest,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    ChangePasswordRequest,
    ChangePinRequest,
)
from app.services.auth_service import (
    register_step1,
    register_step2,
    register_step3,
    login_user,
)
from app.middleware.auth import get_current_user
from app.models.user import User, UserRole, UserStatus
from datetime import datetime, timedelta

from app.utils.tokens import (
    generate_reset_token,
    verify_reset_token,
    generate_pin_reset_token,
    verify_pin_reset_token,
    generate_verification_token,
    verify_verification_token,
)
from app.utils.jwt import create_access_token
from app.services.email_service import send_password_reset_email, send_pin_reset_email, send_verification_email
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType
from app.utils.hashing import hash_password, hash_pin, verify_pin, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register/step1")
def register_step_one(data: RegisterStep1, db: Session = Depends(get_db)):
    user = register_step1(data, db)
    return {
        "message": "Step 1 complete. Proceed to step 2.",
        "user_id": str(user.id)
    }


@router.post("/register/step2/{user_id}")
def register_step_two(user_id: str, data: RegisterStep2, db: Session = Depends(get_db)):
    user = register_step2(user_id, data, db)
    return {
        "message": "Step 2 complete. Proceed to step 3.",
        "user_id": str(user.id)
    }


@router.post("/register/step3/{user_id}", response_model=TokenResponse)
def register_step_three(user_id: str, data: RegisterStep3, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    result = register_step3(user_id, data, db)
    user_email = result["user"].email
    user_first_name = result["user"].first_name
    background_tasks.add_task(
        send_verification_email,
        user_email,
        user_first_name,
        generate_verification_token(user_email)
    )
    return result


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(data, db)
    return result


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(data: LoginRequest, db: Session = Depends(get_db)):
    """Admin login endpoint - skips email verification check"""
    # Find user by email
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is admin
    if user.role != UserRole.admin and user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if user is blocked
    if user.status == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked. Contact support.")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token with admin role
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_to_response(user)
    }


def get_current_admin(current_user: User = Depends(get_current_user)):
    """Dependency to verify user is admin"""
    if current_user.role != UserRole.admin and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return user_to_response(current_user)


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        token = generate_reset_token(user.email)
        send_password_reset_email(user.email, user.first_name, token)
    # Always return success to avoid email enumeration
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = verify_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password reset successfully"}


@router.post("/pin/set")
def set_pin(
    data: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.transaction_pin = hash_pin(data.pin)
    db.commit()
    return {"message": "Transaction PIN set successfully"}


@router.post("/pin-reset/request")
def request_pin_reset(data: PinResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        token = generate_pin_reset_token(user.email)
        send_pin_reset_email(user.email, user.first_name, token)
    return {"message": "If that email exists, a PIN reset link has been sent."}


@router.post("/pin-reset/confirm")
def confirm_pin_reset(data: PinResetConfirm, db: Session = Depends(get_db)):
    email = verify_pin_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.transaction_pin = hash_pin(data.new_pin)
    db.commit()
    return {"message": "PIN reset successfully"}

@router.post("/verify-pin")
def verify_pin_login(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.utils.hashing import verify_pin
    pin = data.get("pin", "")
    
    # Check if PIN is locked
    if current_user.pin_locked_until and current_user.pin_locked_until > datetime.utcnow():
        remaining_minutes = int((current_user.pin_locked_until - datetime.utcnow()).total_seconds() / 60)
        raise HTTPException(
            status_code=403, 
            detail=f"PIN locked. Try again in {remaining_minutes} minutes."
        )
    
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="No PIN set. Please set your PIN first.")
    
    if not verify_pin(pin, current_user.transaction_pin):
        # Increment failed attempts
        current_user.pin_failed_attempts += 1
        remaining_attempts = 5 - current_user.pin_failed_attempts
        
        if current_user.pin_failed_attempts >= 5:
            # Lock PIN for 30 minutes
            current_user.pin_locked_until = datetime.utcnow() + timedelta(minutes=30)
            current_user.pin_failed_attempts = 0
            db.commit()
            raise HTTPException(
                status_code=403, 
                detail="Too many incorrect PIN attempts. PIN locked for 30 minutes."
            )
        
        db.commit()
        raise HTTPException(
            status_code=400, 
            detail=f"Incorrect PIN. {remaining_attempts} attempts remaining."
        )
    
    # Reset failed attempts on successful verification
    current_user.pin_failed_attempts = 0
    current_user.pin_locked_until = None
    db.commit()
    
    return {"message": "PIN verified", "verified": True}


@router.post("/email-verification/request")
def request_email_verification(data: EmailVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user and not user.is_email_verified:
        token = generate_verification_token(user.email)
        send_verification_email(user.email, user.first_name, token)
    # Always return success to avoid email enumeration
    return {"message": "If that email exists and is not verified, a verification link has been sent."}


@router.post("/email-verification/confirm")
def confirm_email_verification(data: EmailVerificationConfirm, db: Session = Depends(get_db)):
    email = verify_verification_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_email_verified:
        return {"message": "Email already verified"}

    user.is_email_verified = True
    db.commit()
    db.refresh(user)

    # Create notification for email verification
    NotificationService.create_notification(
        db,
        user.id,
        "Email Verified",
        "Your email has been successfully verified. You can now access all account features.",
        NotificationType.email
    )
    db.commit()

    return {"message": "Email verified successfully"}


@router.put("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    # Check if user is blocked
    if current_user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=403, 
            detail="Account blocked. Contact support@arcteronbank"
        )
    
    # Update only provided fields
    if data.first_name is not None:
        current_user.first_name = data.first_name
    if data.last_name is not None:
        current_user.last_name = data.last_name
    if data.middle_name is not None:
        current_user.middle_name = data.middle_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.address is not None:
        current_user.address = data.address
    if data.city is not None:
        current_user.city = data.city
    if data.state is not None:
        current_user.state = data.state
    if data.zip_code is not None:
        current_user.zip_code = data.zip_code
    if data.country is not None:
        current_user.country = data.country
    
    db.commit()
    db.refresh(current_user)
    return user_to_response(current_user)


@router.put("/profile-photo", response_model=UserResponse)
def update_profile_photo(
    data: PhotoUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile photo."""
    # Check if user is blocked
    if current_user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=403, 
            detail="Account blocked. Contact support@arcteronbank"
        )
    
    # Validate base64 data
    if not data.photo_data:
        raise HTTPException(status_code=400, detail="No photo data provided")

    if not data.photo_data.startswith('data:image/'):
        raise HTTPException(status_code=400, detail="Invalid image format")

    try:
        # 1. Decode the base64 data to raw byte blocks
        header, encoded = data.photo_data.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        ext = "jpg" if "jpeg" in mime_type else mime_type.split("/")[1]
        
        file_bytes = base64.b64decode(encoded)
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            # 2. Upload to Supabase Storage 'avatars' Bucket via REST API
            filename = f"user_{current_user.id}.{ext}"
            upload_url = f"{supabase_url}/storage/v1/object/avatars/{filename}"
            
            headers = {
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": mime_type,
                "x-upsert": "true"
            }
            
            # Send file synchronously
            with httpx.Client() as client:
                res = client.post(upload_url, headers=headers, content=file_bytes)
                if res.status_code not in (200, 201):
                    raise HTTPException(status_code=500, detail=f"Storage upload failed: {res.text}")
            
            # 3. Store the clean short public URL in PostgreSQL instead of full file data
            public_url = f"{supabase_url}/storage/v1/object/public/avatars/{filename}"
            current_user.profile_photo = public_url
        else:
            # Failsafe if Supabase variables aren't configured yet so database doesn't crash on long Base64 string bounds
            if len(data.photo_data) > 255:
                current_user.profile_photo = f"https://ui-avatars.com/api/?name={current_user.first_name}+{current_user.last_name}"
            else:
                current_user.profile_photo = data.photo_data

        db.commit()
        db.refresh(current_user)
        return user_to_response(current_user)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo processing failed: {str(e)}")


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password (requires current password)."""
    # Verify current password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    db.refresh(current_user)

    # Create notification
    NotificationService.create_notification(
        db,
        current_user.id,
        "Password Changed",
        "Your account password has been successfully changed.",
        NotificationType.security
    )
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/change-pin")
def change_pin(
    data: ChangePinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user PIN (requires current PIN)."""
    # Check if user has a PIN set
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="No PIN set. Please set a PIN first.")

    # Verify current PIN
    if not verify_pin(data.current_pin, current_user.transaction_pin):
        raise HTTPException(status_code=400, detail="Current PIN is incorrect")

    # Update PIN
    current_user.transaction_pin = hash_pin(data.new_pin)
    db.commit()
    db.refresh(current_user)

    # Create notification
    NotificationService.create_notification(
        db,
        current_user.id,
        "PIN Changed",
        "Your transaction PIN has been successfully changed.",
        NotificationType.security
    )
    db.commit()

    return {"message": "PIN changed successfully"}


@router.get("/status")
def get_user_status(current_user: User = Depends(get_current_user)):
    """
    Lightweight endpoint for the frontend to poll and detect if the current
    user's account has been blocked mid-session.
    """
    return {
        "status": current_user.status.value,
        "user_id": str(current_user.id),
        "blocked_reason": current_user.blocked_reason if current_user.status.value == "blocked" else None
    }
```

---

### BACKEND 2: transfers.py
File Path: `backend/app/routers/transfers.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.middleware.auth import get_current_user, get_current_active_user
from app.models.user import User, UserStatus
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.notification import Notification, NotificationType
from app.utils.hashing import verify_pin
from app.utils.account_number import generate_transaction_reference
from app.services.email_service import send_transfer_sent_email, send_transfer_received_email
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


def create_notification(db, user_id, title, message, notif_type, related_id=None, related_type=None, data=None):
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        related_id=related_id,
        related_type=related_type,
        data=data
    )
    db.add(notif)


@router.post("/local")
def local_transfer(
    data: LocalTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify PIN
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="Please set a transaction PIN before making transfers.")
    if not verify_pin(data.pin, current_user.transaction_pin):
        raise HTTPException(status_code=400, detail="Incorrect PIN. Transfer declined.")

    # Check if user is blocked (after PIN verification)
    if current_user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked. You cannot perform a local transfer. Contact support@arcteronbank."
        )

    # Get sender account
    sender_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).first()

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    if sender_account.is_frozen:
        raise HTTPException(status_code=403, detail="Your account is frozen. Contact support.")

    if sender_account.blocked_at:
        raise HTTPException(status_code=403, detail="Transfer blocked. Contact support@arcteronbank")

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
        sender_name=f"{current_user.first_name} {current_user.last_name}",
        recipient_name=f"{recipient_user.first_name} {recipient_user.last_name}",
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
        related_id=transaction.id,
        related_type="transaction",
        data={
            "amount": float(amount),
            "recipient": f"{recipient_user.first_name} {recipient_user.last_name}",
            "reference": reference
        }
    )

    create_notification(
        db, recipient_account.user_id,
        "Money Received",
        f"You received {fmt_amount(amount)} from {current_user.first_name} {current_user.last_name}. Ref: {reference}",
        NotificationType.transaction,
        related_id=transaction.id,
        related_type="transaction",
        data={
            "amount": float(amount),
            "sender": f"{current_user.first_name} {current_user.last_name}",
            "reference": reference
        }
    )

    # Email alerts
    try:
        send_transfer_sent_email(
            to=current_user.email,
            first_name=current_user.first_name,
            amount=fmt_amount(amount),
            reference=reference,
            recipient_name=f"{recipient_user.first_name} {recipient_user.last_name}",
            recipient_account_last_four=recipient_account.account_number[-4:],
            transaction_date=datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC"),
            description=data.description or "Transfer",
            new_balance=fmt_amount(sender_after)
        )
        send_transfer_received_email(
            to=recipient_account.user.email,
            first_name=recipient_account.user.first_name,
            amount=fmt_amount(amount),
            reference=reference,
            sender_name=f"{current_user.first_name} {current_user.last_name}",
            account_last_four=current_user.account.account_number[-4:] if current_user.account else "0000",
            transaction_date=datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC"),
            description=data.description or "Transfer",
            new_balance=fmt_amount(receiver_after)
        )
    except Exception:
        pass  # Never block transfer due to email failure

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify PIN
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="Please set a transaction PIN before making transfers.")
    if not verify_pin(data.pin, current_user.transaction_pin):
        raise HTTPException(status_code=400, detail="Incorrect PIN. Transfer declined.")

    # Check if user is blocked (after PIN verification)
    if current_user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked. You cannot perform an international transfer. Contact support@arcteronbank."
        )

    # Get sender account
    sender_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).first()

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found.")

    if sender_account.is_frozen:
        raise HTTPException(status_code=403, detail="Your account is frozen. Contact support.")

    if sender_account.blocked_at:
        raise HTTPException(status_code=403, detail="Transfer blocked. Contact support@arcteronbank")

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
        sender_name=f"{current_user.first_name} {current_user.last_name}",
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
        related_id=transaction.id,
        related_type="transaction",
        data={
            "amount": float(amount),
            "recipient": data.recipient_name,
            "bank": data.recipient_bank,
            "reference": reference
        }
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
```

---

### BACKEND 3: admin.py
File Path: `backend/app/routers/admin.py`

```python
from fastapi import APIRouter, Depends, HTTPException
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


# Helper functions
def generate_cot_code():
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
    admin_transaction = AdminTransaction(
        admin_id=current_admin.id,
        user_id=user.id,
        transaction_type=AdminTransactionType.credit,
        amount=Decimal(str(data.amount)),
        sender_name=data.sender_name,
        bank_name=data.bank_name,
        transfer_type=AdminTransferType(data.transfer_type) if data.transfer_type in ["local", "international"] else None,
        description=data.description,
        account_number=data.account_number,
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

    # Notify blocked user
    from app.models.notification import NotificationType as NT
    NotificationService.create_notification(
        db,
        user.id,
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
    code = generate_cot_code()
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
    """Delete a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    
    # Delete user's account
    account = db.query(Account).filter(Account.user_id == user.id).first()
    if account:
        db.delete(account)
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


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
```

---

### BACKEND 4: auth_service.py
File Path: `backend/app/services/auth_service.py`

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from app.models.user import User, UserRole, UserStatus
from app.models.account import Account
from app.schemas.user import (
    RegisterStep1,
    RegisterStep2,
    RegisterStep3,
    LoginRequest,
    user_to_response,
)
from app.utils.hashing import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.utils.account_number import generate_account_number
from app.services.email_service import send_login_alert, send_verification_email
from app.utils.tokens import generate_verification_token
import traceback
import re


def register_step1(data: RegisterStep1, db: Session) -> User:
    # Check email exists
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check phone exists
    if db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=UserRole.user,
        status=UserStatus.active,
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

    # Handle SSN
    ssn_last_four = None
    ssn_encrypted = None
    if data.ssn:
        cleaned_ssn = data.ssn.replace("-", "")
        ssn_last_four = cleaned_ssn[-4:]
        # In production use proper encryption - for educational purposes we store hashed
        ssn_encrypted = hash_password(cleaned_ssn)

    user.date_of_birth = data.date_of_birth
    user.citizenship_status = data.citizenship_status
    user.ssn_last_four = ssn_last_four
    user.ssn_encrypted = ssn_encrypted
    user.itin = data.itin
    user.address = data.address
    user.city = data.city
    user.state = data.state
    user.zip_code = data.zip_code
    user.country = data.country

    db.commit()
    db.refresh(user)
    return user


def register_step3(user_id: str, data: RegisterStep3, db: Session) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.id_type = data.id_type
    user.id_number = data.id_number
    user.id_expiry_date = data.id_expiry_date
    user.employment_status = data.employment_status
    user.employer_name = data.employer_name
    user.annual_income = data.annual_income
    user.source_of_income = data.source_of_income
    user.account_purpose = data.account_purpose
    user.is_kyc_complete = True

    # Check if account already exists (prevents duplicate on retry)
    existing_account = db.query(Account).filter(Account.user_id == user.id).first()
    if not existing_account:
        account_number = generate_account_number(db)
        account = Account(
            user_id=user.id,
            account_number=account_number,
            routing_number="021000021",
            account_type="checking",
            balance=0.00,
            currency="USD",
            swift_code="ARCTUSD1",
            bank_name="Arcteron Trust"
        )
        db.add(account)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return {"access_token": token, "token_type": "bearer", "user": user_to_response(user)}


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

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Send login alert email
    try:
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
```

---

### BACKEND 5: user.py model
File Path: `backend/app/models/user.py`

```python
import uuid
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, Date, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    blocked = "blocked"


class IDType(str, enum.Enum):
    drivers_license = "drivers_license"
    passport = "passport"
    state_id = "state_id"
    military_id = "military_id"


class CitizenshipStatus(str, enum.Enum):
    us_citizen = "us_citizen"
    permanent_resident = "permanent_resident"
    visa_holder = "visa_holder"
    other = "other"


class EmploymentStatus(str, enum.Enum):
    employed = "employed"
    self_employed = "self_employed"
    unemployed = "unemployed"
    student = "student"
    retired = "retired"


class AccountPurpose(str, enum.Enum):
    personal = "personal"
    savings = "savings"
    business = "business"
    investment = "investment"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # --- Basic Info (Registration Step 1) ---
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    transaction_pin = Column(String(255), nullable=True)

    # --- Personal Details (Registration Step 2) ---
    date_of_birth = Column(Date, nullable=True)
    citizenship_status = Column(Enum(CitizenshipStatus), nullable=True)
    ssn_last_four = Column(String(4), nullable=True)      # last 4 digits of SSN
    ssn_encrypted = Column(String(255), nullable=True)    # full SSN encrypted
    itin = Column(String(20), nullable=True)              # for non-US citizens

    # --- Address (Registration Step 2) ---
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True, default="United States")

    # --- Government ID (Registration Step 3) ---
    id_type = Column(Enum(IDType), nullable=True)
    id_number = Column(String(100), nullable=True)
    id_expiry_date = Column(Date, nullable=True)
    id_front_image = Column(String(255), nullable=True)   # file path
    id_back_image = Column(String(255), nullable=True)    # file path

    # --- Financial Info (Registration Step 3) ---
    employment_status = Column(Enum(EmploymentStatus), nullable=True)
    employer_name = Column(String(200), nullable=True)
    annual_income = Column(String(50), nullable=True)     # stored as range e.g "$50,000 - $75,000"
    source_of_income = Column(String(200), nullable=True)
    account_purpose = Column(Enum(AccountPurpose), nullable=True)

    # --- Profile ---
    profile_photo = Column(String(255), nullable=True)

    # --- Role & Status ---
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.active, nullable=False)
    is_email_verified = Column(Boolean, default=False)
    is_kyc_complete = Column(Boolean, default=False)
    is_id_verified = Column(Boolean, default=False)

    # --- PIN Security ---
    pin_failed_attempts = Column(Integer, default=0)
    pin_locked_until = Column(DateTime, nullable=True)       # admin manually verifies

    # --- Blocking Info ---
    blocked_at = Column(DateTime, nullable=True)
    blocked_reason = Column(Text, nullable=True)

    # --- Timestamps ---
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # --- Relationships ---
    account = relationship("Account", back_populates="user", uselist=False)
    transactions_sent = relationship(
        "Transaction",
        foreign_keys="Transaction.sender_id",
        back_populates="sender"
    )
    transactions_received = relationship(
        "Transaction",
        foreign_keys="Transaction.receiver_id",
        back_populates="receiver"
    )
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="admin")
```

---

### BACKEND 6: transaction.py model
File Path: `backend/app/models/transaction.py`

```python
import uuid
from sqlalchemy import Column, String, Numeric, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
from app.database import Base


class TransactionType(str, enum.Enum):
    local_transfer = "local_transfer"
    international_transfer = "international_transfer"
    credit = "credit"
    debit = "debit"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    reversed = "reversed"


class TransactionCategory(str, enum.Enum):
    transfer = "transfer"
    deposit = "deposit"
    withdrawal = "withdrawal"
    fee = "fee"
    adjustment = "adjustment"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Transaction details
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(String(10), default="USD")
    transaction_type = Column(Enum(TransactionType), nullable=False)
    category = Column(Enum(TransactionCategory), default=TransactionCategory.transfer)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    description = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)

    # For local transfers
    sender_account_number = Column(String(20), nullable=True)
    receiver_account_number = Column(String(20), nullable=True)

    # For international transfers
    recipient_name = Column(String(200), nullable=True)
    recipient_bank = Column(String(200), nullable=True)
    recipient_bank_address = Column(String(255), nullable=True)
    recipient_account = Column(String(100), nullable=True)
    recipient_swift = Column(String(50), nullable=True)
    recipient_country = Column(String(100), nullable=True)
    recipient_routing = Column(String(50), nullable=True)

    # Codes (COT, BOP etc)
    requires_code = Column(Boolean, default=False)
    code_type = Column(String(50), nullable=True)
    code_value = Column(String(100), nullable=True)
    code_verified = Column(Boolean, default=False)

    # Balances snapshot
    sender_balance_before = Column(Numeric(precision=18, scale=2), nullable=True)
    sender_balance_after = Column(Numeric(precision=18, scale=2), nullable=True)
    receiver_balance_before = Column(Numeric(precision=18, scale=2), nullable=True)
    receiver_balance_after = Column(Numeric(precision=18, scale=2), nullable=True)

    # Admin control
    created_by_admin = Column(Boolean, default=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="transactions_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="transactions_received")
```

---

### FRONTEND 7: transfer.js
File Path: `frontend/pages/user/js/transfer.js`

```js
/* File is empty */

```

---

### FRONTEND 8: transfer.html
File Path: `frontend/pages/user/transfer.html`

```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Transfer — Arcteron Trust</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap"
    rel="stylesheet">
  <link rel="stylesheet" href="../../assets/css/theme.css">
  <link rel="stylesheet" href="../../assets/css/style.css">
  <script src="../../assets/js/theme.js"></script>
  <style>
    body {
      font-family: 'DM Sans', sans-serif;
      margin: 0;
    }

    .layout {
      display: flex;
      min-height: 100vh;
    }

    /* ── Sidebar ── */
    .sidebar {
      width: 260px;
      background: var(--bg-secondary);
      border-right: none;
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0;
      left: 0;
      height: 100vh;
      z-index: 300;
      transition: transform 0.3s ease;
    }

    .sidebar-logo {
      padding: 0 20px;
      height: 60px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }

    .sidebar-logo-icon {
      width: 28px;
      height: 28px;
      flex-shrink: 0;
      opacity: 0.8;
    }

    .sidebar-logo-text h1 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 16px;
      font-weight: 600;
      color: #ffffff;
      line-height: 1.2;
    }

    .sidebar-logo-text p {
      font-size: 9px;
      color: rgba(255, 255, 255, 0.3);
      margin-top: 1px;
      letter-spacing: 2px;
      text-transform: uppercase;
    }

    .sidebar-nav {
      padding: 10px 10px;
      flex: 1;
      overflow-y: auto;
    }

    .nav-section-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: rgba(255, 255, 255, 0.25);
      padding: 10px 10px 4px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.5);
      cursor: pointer;
      transition: all 0.2s;
      margin-bottom: 1px;
      text-decoration: none;
    }

    .nav-item:hover {
      background: rgba(255, 255, 255, 0.07);
      color: rgba(255, 255, 255, 0.85);
    }

    .nav-item.active {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
      font-weight: 600;
    }

    .nav-item svg {
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .nav-item.danger {
      color: rgba(239, 68, 68, 0.7);
    }

    .nav-item.danger:hover {
      background: rgba(239, 68, 68, 0.1);
      color: #EF4444;
    }

    .sidebar-footer {
      padding: 12px 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .user-card {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;
      margin-bottom: 4px;
    }

    .user-card:hover {
      background: rgba(255, 255, 255, 0.07);
    }

    .sidebar-avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      flex-shrink: 0;
      font-family: 'Cormorant Garamond', serif;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .user-name {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.85);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.3);
    }

    /* Main */
    .main-content {
      margin-left: 260px;
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      background: var(--bg-primary);
    }

    /* ── Topbar ── */
    .topbar {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      padding: 0 28px;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 200;
      flex-shrink: 0;
    }

    .topbar-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .menu-btn {
      display: none;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: var(--text-secondary);
      flex-shrink: 0;
    }

    .topbar-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .icon-btn {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: var(--text-secondary);
      transition: all 0.2s;
      position: relative;
      text-decoration: none;
    }

    .icon-btn:hover {
      color: var(--text-primary);
      background: var(--border-color);
    }

    .notif-dot {
      min-width: 16px;
      height: 16px;
      background: #EF4444;
      border-radius: 50%;
      position: absolute;
      top: 5px;
      right: 5px;
      border: 2px solid var(--bg-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      font-weight: 600;
      color: white;
      padding: 0 4px;
    }

    .topbar-avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: #111827;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      flex-shrink: 0;
      font-family: 'Cormorant Garamond', serif;
    }

    [data-theme="dark"] .main-content .topbar-avatar {
      background: #E5E7EB;
      color: #111827;
    }

    .page-content {
      padding: 28px;
      flex: 1;
    }

    /* Page header */
    .page-header {
      margin-bottom: 24px;
    }

    .page-header h1 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 26px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .page-header p {
      font-size: 13px;
      color: var(--text-secondary);
      margin-top: 4px;
    }

    /* Transfer type tabs */
    .transfer-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 24px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 4px;
      width: fit-content;
    }

    .tab-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.2s;
      background: none;
      border: none;
      font-family: 'DM Sans', sans-serif;
    }

    .tab-btn:hover {
      color: var(--text-primary);
    }

    .tab-btn.active {
      background: var(--text-primary);
      color: var(--bg-secondary);
      font-weight: 600;
    }

    .tab-btn svg {
      width: 14px;
      height: 14px;
    }

    /* Balance pill */
    .balance-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 16px;
      margin-bottom: 24px;
      font-size: 13px;
      color: var(--text-secondary);
    }

    .balance-pill strong {
      color: var(--text-primary);
      font-weight: 700;
    }

    .balance-pill-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10B981;
    }

    /* Form panels */
    .transfer-panel {
      display: none;
    }

    .transfer-panel.active {
      display: block;
    }

    .transfer-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      align-items: start;
    }

    /* Form card */
    .form-card {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 28px;
    }

    .form-card-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .form-card-title svg {
      width: 16px;
      height: 16px;
      color: var(--text-muted);
    }

    .field {
      margin-bottom: 16px;
    }

    .field label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 7px;
    }

    .field input,
    .field select,
    .field textarea {
      width: 100%;
      background: var(--bg-primary);
      border: 1.5px solid var(--border-color);
      border-radius: 8px;
      padding: 11px 14px;
      font-size: 14px;
      color: var(--text-primary);
      font-family: 'DM Sans', sans-serif;
      transition: border-color 0.2s, box-shadow 0.2s;
      outline: none;
      box-sizing: border-box;
      appearance: none;
    }

    .field textarea {
      resize: vertical;
      min-height: 80px;
    }

    .field input::placeholder,
    .field textarea::placeholder {
      color: var(--text-muted);
      font-size: 13px;
    }

    .field input:focus,
    .field select:focus,
    .field textarea:focus {
      border-color: var(--text-primary);
      box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.06);
    }

    [data-theme="dark"] .field input:focus,
    [data-theme="dark"] .field select:focus,
    [data-theme="dark"] .field textarea:focus {
      box-shadow: 0 0 0 3px rgba(229, 231, 235, 0.06);
    }

    [data-theme="dark"] .field input,
    [data-theme="dark"] .field select,
    [data-theme="dark"] .field textarea {
      background: #0F1115;
      border-color: #2B2F36;
      color: #E5E7EB;
    }

    [data-theme="light"] .field input,
    [data-theme="light"] .field select,
    [data-theme="light"] .field textarea {
      background: #F9FAFB;
    }

    .field input::placeholder {
      color: var(--text-muted);
    }

    .field input.error-field,
    .field textarea.error-field {
      border-color: #EF4444;
      background: rgba(239, 68, 68, 0.02);
    }

    .field-error {
      display: none;
      font-size: 11px;
      color: #EF4444;
      margin-top: 5px;
      font-weight: 500;
    }

    .field-error.show {
      display: block;
    }

    /* Slick searchable dropdown */
    .search-select {
      position: relative;
      user-select: none;
    }

    .search-select-trigger {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      background: var(--bg-primary);
      border: 1.5px solid var(--border-color);
      border-radius: 8px;
      padding: 11px 14px;
      font-size: 14px;
      color: var(--text-primary);
      cursor: pointer;
      transition: all 0.2s;
    }

    .search-select.open .search-select-trigger {
      border-color: var(--text-primary);
      border-radius: 8px 8px 0 0;
    }

    .search-select-options {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: var(--bg-secondary);
      border: 1.5px solid var(--text-primary);
      border-top: none;
      border-radius: 0 0 8px 8px;
      max-height: 250px;
      overflow-y: auto;
      z-index: 1000;
      display: none;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    }

    .search-select.open .search-select-options {
      display: block;
    }

    .search-select-search {
      position: sticky;
      top: 0;
      padding: 10px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
    }

    .search-select-search input {
      width: 100%;
      padding: 8px 12px;
      font-size: 13px;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      background: var(--bg-primary);
      color: var(--text-primary);
      outline: none;
    }

    .search-option {
      padding: 10px 14px;
      font-size: 13px;
      color: var(--text-secondary);
      cursor: pointer;
      transition: background 0.15s;
    }

    .search-option:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-primary);
    }

    /* Verification dots */
    .verifying-dots {
      display: none;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 500;
    }

    .verifying-dots.show {
      display: flex;
    }

    .verifying-dots span {
      width: 4px;
      height: 4px;
      background: currentColor;
      border-radius: 50%;
      animation: bounce 1s infinite;
    }

    .verifying-dots span:nth-child(2) {
      animation-delay: 0.2s;
    }

    .verifying-dots span:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes bounce {

      0%,
      100% {
        transform: translateY(0);
        opacity: 0.3;
      }

      50% {
        transform: translateY(-3px);
        opacity: 1;
      }
    }


    .field-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    /* Amount input */
    .amount-wrap {
      position: relative;
    }

    .amount-wrap input {
      padding-left: 36px;
      font-size: 20px;
      font-weight: 600;
      height: 52px;
    }

    .amount-prefix {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 18px;
      font-weight: 600;
      color: var(--text-muted);
      pointer-events: none;
    }

    /* Account verify */
    .verify-row {
      display: flex;
      gap: 8px;
      align-items: flex-end;
    }

    .verify-row .field {
      flex: 1;
      margin-bottom: 0;
    }

    .verify-btn {
      height: 42px;
      padding: 0 16px;
      background: var(--bg-primary);
      border: 1.5px solid var(--border-color);
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.2s;
      font-family: 'DM Sans', sans-serif;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .verify-btn:hover {
      color: var(--text-primary);
      border-color: var(--text-primary);
    }

    .verified-badge {
      display: none;
      align-items: center;
      gap: 6px;
      padding: 10px 14px;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 8px;
      margin-top: 8px;
      font-size: 13px;
      font-weight: 500;
      color: #10B981;
    }

    .verified-badge.show {
      display: flex;
    }

    .verified-badge svg {
      width: 14px;
      height: 14px;
      flex-shrink: 0;
    }

    /* PIN input */
    .pin-row {
      display: flex;
      gap: 10px;
      justify-content: center;
      margin: 4px 0;
    }

    .pin-digit {
      width: 48px;
      height: 52px;
      border: 1.5px solid var(--border-color);
      border-radius: 8px;
      background: var(--bg-primary);
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
      text-align: center;
      font-family: 'DM Sans', sans-serif;
      transition: border-color 0.2s, box-shadow 0.2s;
      outline: none;
    }

    .pin-digit:focus {
      border-color: var(--text-primary);
      box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.06);
    }

    [data-theme="dark"] .pin-digit {
      background: #0F1115;
      border-color: #2B2F36;
      color: #E5E7EB;
    }

    [data-theme="dark"] .pin-digit:focus {
      border-color: #E5E7EB;
      box-shadow: 0 0 0 3px rgba(229, 231, 235, 0.06);
    }

    /* Submit button */
    .submit-btn {
      width: 100%;
      background: #111827;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 14px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s, transform 0.15s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      min-height: 50px;
      margin-top: 8px;
    }

    [data-theme="dark"] .submit-btn {
      background: #E5E7EB;
      color: #0F1115;
    }

    .submit-btn:hover:not(:disabled) {
      opacity: 0.85;
    }

    .submit-btn:active:not(:disabled) {
      transform: scale(0.99);
    }

    .submit-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .dot-loader {
      display: none;
      align-items: center;
      gap: 4px;
    }

    .dot-loader span {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: #fff;
      animation: dotBounce 1.2s ease-in-out infinite;
    }

    [data-theme="dark"] .dot-loader span {
      background: #0F1115;
    }

    .dot-loader span:nth-child(2) {
      animation-delay: 0.2s;
    }

    .dot-loader span:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes dotBounce {

      0%,
      80%,
      100% {
        transform: scale(0.7);
        opacity: 0.4;
      }

      40% {
        transform: scale(1);
        opacity: 1;
      }
    }

    /* Alert */
    .form-alert {
      display: none;
      padding: 11px 14px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 14px;
      border-left: 3px solid;
      align-items: flex-start;
      gap: 10px;
    }

    .form-alert.show {
      display: flex;
    }

    .form-alert.error {
      background: rgba(239, 68, 68, 0.06);
      border-color: #EF4444;
      color: #DC2626;
    }

    .form-alert.success {
      background: rgba(16, 185, 129, 0.06);
      border-color: #10B981;
      color: #059669;
    }

    [data-theme="dark"] .form-alert.error {
      background: rgba(239, 68, 68, 0.1);
      color: #FCA5A5;
    }

    [data-theme="dark"] .form-alert.success {
      background: rgba(16, 185, 129, 0.1);
      color: #6EE7B7;
    }

    /* Summary card */
    .summary-card {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 24px;
      position: sticky;
      top: 80px;
    }

    .summary-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border-color);
    }

    .summary-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      font-size: 13px;
    }

    .summary-label {
      color: var(--text-muted);
      font-size: 12px;
    }

    .summary-value {
      color: var(--text-primary);
      font-weight: 500;
      text-align: right;
      max-width: 60%;
      word-break: break-all;
    }

    .summary-divider {
      height: 1px;
      background: var(--border-color);
      margin: 14px 0;
    }

    .summary-total {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .summary-total-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .summary-total-value {
      font-family: 'Cormorant Garamond', serif;
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .summary-note {
      margin-top: 14px;
      padding: 10px 12px;
      background: var(--bg-primary);
      border-radius: 8px;
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.5;
    }

    /* Success modal */
    .modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);
    }

    .modal-overlay.show {
      display: flex;
    }

    .modal {
      background: var(--bg-secondary);
      border-radius: 16px;
      padding: 40px;
      max-width: 400px;
      width: 90%;
      text-align: center;
      border: 1px solid var(--border-color);
      animation: modalIn 0.3s ease;
    }

    @keyframes modalIn {
      from {
        transform: scale(0.9);
        opacity: 0;
      }

      to {
        transform: scale(1);
        opacity: 1;
      }
    }

    /* Receipt Modal */
    .receipt-modal-header {
      padding: 24px;
      background: #111827;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .receipt-modal-header h2 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 20px;
      margin: 0;
      font-weight: 600;
    }

    .receipt-modal-body {
      padding: 24px;
    }

    .receipt-amount-box {
      text-align: center;
      padding: 20px 0;
      border-bottom: 1px dashed var(--border-color);
      margin-bottom: 20px;
    }

    .receipt-amount {
      font-family: 'Cormorant Garamond', serif;
      font-size: 32px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .receipt-amount.credit {
      color: #10B981;
    }

    .receipt-amount.debit {
      color: #EF4444;
    }

    .receipt-status-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      background: var(--bg-primary);
      margin-top: 8px;
    }

    .receipt-info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }

    .receipt-info-item label {
      display: block;
      font-size: 10px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 4px;
    }

    .receipt-info-item p {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-primary);
      margin: 0;
    }

    .receipt-modal-footer {
      padding: 20px 24px 24px;
      display: flex;
      gap: 12px;
    }

    .btn-receipt-dl {
      flex: 1;
      height: 44px;
      background: #111827;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      font-family: 'DM Sans', sans-serif;
    }

    [data-theme="dark"] .btn-receipt-dl {
      background: #E5E7EB;
      color: #111827;
    }

    .btn-receipt-dl:hover {
      opacity: 0.9;
    }

    .btn-receipt-close {
      width: auto;
      height: 44px;
      padding: 0 16px;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary);
      cursor: pointer;
      background: transparent;
      font-size: 14px;
      font-weight: 500;
    }

    .btn-receipt-close:hover {
      color: var(--text-primary);
      border-color: var(--text-primary);
    }

    .modal-icon {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;
    }

    .modal-icon svg {
      color: #10B981;
    }

    .modal h2 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .modal p {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.6;
      margin-bottom: 6px;
    }

    .modal-ref {
      display: inline-block;
      background: var(--bg-primary);
      border-radius: 6px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      letter-spacing: 0.5px;
      margin: 10px 0 20px;
    }

    .modal-pending-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.2);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
      color: #F59E0B;
      margin-bottom: 16px;
    }

    .modal-btn {
      width: 100%;
      background: #111827;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 13px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
      margin-bottom: 8px;
    }

    [data-theme="dark"] .modal-btn {
      background: #E5E7EB;
      color: #0F1115;
    }

    .modal-btn:hover {
      opacity: 0.85;
    }

    .modal-btn-outline {
      width: 100%;
      background: transparent;
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .modal-btn-outline:hover {
      color: var(--text-primary);
      border-color: var(--text-primary);
    }

    /* COT/BOP info box */
    .code-info-box {
      background: rgba(245, 158, 11, 0.06);
      border: 1px solid rgba(245, 158, 11, 0.15);
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 12px;
      color: #92400E;
      line-height: 1.6;
      margin-bottom: 14px;
      display: none;
    }

    [data-theme="dark"] .code-info-box {
      color: #FCD34D;
      background: rgba(245, 158, 11, 0.08);
    }

    .code-info-box.show {
      display: block;
    }

    /* Sidebar overlay */
    .sidebar-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.6);
      z-index: 299;
      backdrop-filter: blur(2px);
    }

    .sidebar-overlay.show {
      display: block;
    }

    @media (max-width: 1024px) {
      .transfer-grid {
        grid-template-columns: 1fr;
      }

      .summary-card {
        position: static;
      }
    }

    @media (max-width: 900px) {
      .sidebar {
        transform: translateX(-260px);
      }

      .sidebar.open {
        transform: translateX(0);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
      }

      .main-content {
        margin-left: 0;
      }

      .menu-btn {
        display: flex;
      }

      .page-content {
        padding: 16px;
      }

      .topbar {
        padding: 0 16px;
      }

      .transfer-tabs {
        width: 100%;
      }

      .tab-btn {
        flex: 1;
        justify-content: center;
      }
    }

    @media (max-width: 480px) {
      .field-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <div class="layout layout--fixed-sidebar">

    <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

    <!-- Sidebar -->
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <svg class="sidebar-logo-icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="20" cy="20" r="18" stroke="white" stroke-width="1.5" opacity="0.3" />
          <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="white" opacity="0.9" />
          <path d="M14 23 H26" stroke="white" stroke-width="1.5" opacity="0.6" />
          <circle cx="20" cy="6" r="2" fill="white" opacity="0.5" />
        </svg>
        <div class="sidebar-logo-text">
          <h1>Arcteron Trust</h1>
          <p>Private Banking</p>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section-label">Main</div>
        <a class="nav-item" href="dashboard.html" onclick="nav(event,'dashboard.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          Dashboard
        </a>
        <a class="nav-item active" href="transfer.html" onclick="nav(event,'transfer.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          Transfer
        </a>
        <a class="nav-item" href="transactions.html" onclick="nav(event,'transactions.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
          Transactions
        </a>
        <a class="nav-item" href="cards.html" onclick="nav(event,'cards.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
            <line x1="1" y1="10" x2="23" y2="10"></line>
          </svg>
          Cards
        </a>
        <a class="nav-item" href="notifications.html" onclick="nav(event,'notifications.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          Notifications
        </a>

        <a class="nav-item" href="loans.html" onclick="nav(event,'loans.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
          </svg>
          Loans
        </a>


        <div class="nav-section-label">Account</div>
        <a class="nav-item" href="profile.html" onclick="nav(event,'profile.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          Profile
        </a>

        <a class="nav-item" href="support.html" onclick="nav(event,'support.html')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
          </svg>
          Support
        </a>

      </nav>

      <div class="sidebar-footer">
        <div class="user-card">
          <div class="sidebar-avatar" id="sidebarAvatar">AT</div>
          <div style="flex:1;min-width:0;">
            <div class="user-name" id="sidebarName">Loading...</div>
            <div class="user-role">Personal Account</div>
          </div>
        </div>
        <a class="nav-item danger" onclick="Auth.logout()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign Out
        </a>
      </div>
    </aside>

    <!-- Main -->
    <div class="main-content">
      <header class="topbar">
        <div class="topbar-left">
          <button class="menu-btn" id="menuBtn" onclick="openSidebar()">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span class="topbar-title">Transfer</span>
        </div>
        <div class="topbar-right">
          <button class="icon-btn" onclick="Theme.toggle()">
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          </button>
          <div class="icon-btn-wrapper" style="position:relative">
            <button class="icon-btn" id="notifBtn" onclick="nav(event,'notifications.html')">
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              <div class="notif-dot" id="notifDot" style="display:none">0</div>
            </button>
          </div>
          <div class="topbar-avatar" id="topbarAvatar" onclick="nav(event,'profile.html')">AT</div>
        </div>
      </header>

      <main class="page-content">

        <div class="page-header">
          <h1>Send Money</h1>
          <p>Transfer funds locally or internationally with ease.</p>
        </div>

        <!-- Balance pill -->
        <div class="balance-pill">
          <div class="balance-pill-dot"></div>
          Available Balance: <strong id="availableBalance">Loading...</strong>
        </div>

        <!-- Tabs -->
        <div class="transfer-tabs">
          <button class="tab-btn active" id="tabLocal" onclick="switchTab('local')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
            Local Transfer
          </button>
          <button class="tab-btn" id="tabIntl" onclick="switchTab('international')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            International
          </button>
        </div>

        <!-- Alert -->
        <div id="formAlert" class="form-alert error">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
            style="flex-shrink:0;margin-top:1px">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span id="alertText"></span>
        </div>

        <!-- ── LOCAL TRANSFER ── -->
        <div class="transfer-panel active" id="panelLocal">
          <div class="transfer-grid">

            <div class="form-card">
              <div class="form-card-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                  stroke-linejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                Recipient Details
              </div>

              <div class="field">
                <label>Recipient Account Number</label>
                <div class="verify-row">
                  <div class="field" style="margin-bottom:0">
                    <input type="text" id="localAccNumber" placeholder="Enter 10-digit account number" maxlength="10"
                      oninput="onAccNumberInput()">
                  </div>
                </div>
                <div class="verifying-dots" id="verifyingDots">
                  <span></span><span></span><span></span>
                  <p style="margin:0 0 0 8px">Verifying...</p>
                </div>
                <div class="verified-badge" id="verifiedBadge">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span id="verifiedName">Account verified</span>
                </div>
                <span class="field-error" id="error_localAccNumber"></span>
              </div>

              <div class="field">
                <label>Amount (USD)</label>
                <div class="amount-wrap">
                  <span class="amount-prefix">$</span>
                  <input type="number" id="localAmount" placeholder="0.00" min="1" step="0.01"
                    oninput="updateSummary()">
                </div>
                <span class="field-error" id="error_localAmount"></span>
              </div>

              <div class="field">
                <label>Description <span
                    style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;">(optional)</span></label>
                <textarea id="localDesc" placeholder="What's this transfer for?"></textarea>
              </div>

              <div class="field">
                <label>Transaction PIN</label>
                <div class="pin-row">
                  <input class="pin-digit" id="lpin1" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="lpin2" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="lpin3" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="lpin4" type="password" maxlength="1" inputmode="numeric">
                </div>
              </div>

              <button class="submit-btn" id="localSubmitBtn" onclick="submitLocalTransfer()">
                <span class="btn-text">Send Money</span>
                <div class="dot-loader" id="localDots"><span></span><span></span><span></span></div>
              </button>
            </div>

            <!-- Summary -->
            <div class="summary-card" id="localSummary">
              <div class="summary-title">Transfer Summary</div>

              <div class="summary-row">
                <span class="summary-label">From</span>
                <span class="summary-value" id="summFromName">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">From Account</span>
                <span class="summary-value" id="summFromAcc">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">To</span>
                <span class="summary-value" id="summToName">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">To Account</span>
                <span class="summary-value" id="summToAcc">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">Description</span>
                <span class="summary-value" id="summDesc">—</span>
              </div>

              <div class="summary-divider"></div>

              <div class="summary-total">
                <span class="summary-total-label">Total Amount</span>
                <span class="summary-total-value" id="summAmount">$0.00</span>
              </div>

              <div class="summary-note">
                ✓ Local transfers are instant and free of charge. Funds will be available immediately.
              </div>
            </div>

          </div>
        </div>

        <!-- ── INTERNATIONAL TRANSFER ── -->
        <div class="transfer-panel" id="panelIntl">
          <div class="transfer-grid">

            <div class="form-card">
              <div class="form-card-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                  stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                </svg>
                Recipient Details
              </div>

              <div class="field">
                <label>Recipient Full Name</label>
                <input type="text" id="intlName" placeholder="As shown on bank account" oninput="updateIntlSummary()">
                <span class="field-error" id="error_intlName"></span>
              </div>

              <div class="field-row">
                <div class="field">
                  <label>Recipient Bank</label>
                  <input type="text" id="intlBank" placeholder="Bank name" oninput="updateIntlSummary()">
                  <span class="field-error" id="error_intlBank"></span>
                </div>
                <div class="field">
                  <label>Country</label>
                  <div class="search-select" id="countrySelect">
                    <div class="search-select-trigger" onclick="toggleCountrySelect()">
                      <span id="selectedCountry">Select Country</span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        stroke-width="2">
                        <path d="M6 9l6 6 6-6" />
                      </svg>
                    </div>
                    <div class="search-select-options" id="countryOptions">
                      <div class="search-select-search">
                        <input type="text" placeholder="Search country..." oninput="filterCountries(this.value)"
                          onclick="event.stopPropagation()">
                      </div>
                      <div id="countryList">
                        <!-- Populated by JS -->
                      </div>
                    </div>
                  </div>
                  <span class="field-error" id="error_intlCountry"></span>
                </div>
              </div>

              <div class="field">
                <label>Bank Address <span
                    style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;">(optional)</span></label>
                <input type="text" id="intlBankAddress" placeholder="Bank street address">
              </div>

              <div class="field-row">
                <div class="field">
                  <label>Account / IBAN Number</label>
                  <input type="text" id="intlAccount" placeholder="Account or IBAN">
                  <span class="field-error" id="error_intlAccount"></span>
                </div>
                <div class="field">
                  <label>SWIFT / BIC Code</label>
                  <input type="text" id="intlSwift" placeholder="e.g. BARCGB22"
                    oninput="this.value = this.value.toUpperCase()">
                  <span class="field-error" id="error_intlSwift"></span>
                </div>
              </div>

              <div class="field">
                <label>Routing Number <span
                    style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;">(if
                    applicable)</span></label>
                <input type="text" id="intlRouting" placeholder="ABA routing number">
              </div>

              <div class="field">
                <label>Amount (USD)</label>
                <div class="amount-wrap">
                  <span class="amount-prefix">$</span>
                  <input type="number" id="intlAmount" placeholder="0.00" min="10" step="0.01"
                    oninput="updateIntlSummary(); checkCodeRequirement()">
                </div>
                <span class="field-error" id="error_intlAmount"></span>
              </div>

              <!-- COT/BOP notice -->
              <div class="code-info-box" id="codeInfoBox">
                ⚠️ Transfers of $10,000 or more require a COT (Cost of Transfer) or BOP (Balance of Payment) code.
                Please contact your account manager or visit a branch to obtain this code before proceeding.
              </div>

              <div class="field" id="cotField" style="display:none">
                <label>COT Code</label>
                <input type="text" id="cotCode" placeholder="Enter COT code"
                  oninput="this.value = this.value.toUpperCase()">
              </div>

              <div class="field" id="bopField" style="display:none">
                <label>BOP Code <span
                    style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;">(alternative to
                    COT)</span></label>
                <input type="text" id="bopCode" placeholder="Enter BOP code"
                  oninput="this.value = this.value.toUpperCase()">
              </div>

              <div class="field">
                <label>Transfer Purpose / Description</label>
                <textarea id="intlDesc" placeholder="Reason for transfer (required for international wires)"
                  oninput="updateIntlSummary()"></textarea>
                <span class="field-error" id="error_intlDesc"></span>
              </div>

              <div class="field">
                <label>Transaction PIN</label>
                <div class="pin-row">
                  <input class="pin-digit" id="ipin1" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="ipin2" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="ipin3" type="password" maxlength="1" inputmode="numeric">
                  <input class="pin-digit" id="ipin4" type="password" maxlength="1" inputmode="numeric">
                </div>
              </div>

              <button class="submit-btn" id="intlSubmitBtn" onclick="submitIntlTransfer()">
                <span class="btn-text">Submit Wire Transfer</span>
                <div class="dot-loader" id="intlDots"><span></span><span></span><span></span></div>
              </button>
            </div>

            <!-- Summary -->
            <div class="summary-card" id="intlSummaryCard">
              <div class="summary-title">Wire Transfer Summary</div>

              <div class="summary-row">
                <span class="summary-label">Recipient</span>
                <span class="summary-value" id="isummName">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">Bank</span>
                <span class="summary-value" id="isummBank">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">Country</span>
                <span class="summary-value" id="isummCountry">—</span>
              </div>
              <div class="summary-row">
                <span class="summary-label">Purpose</span>
                <span class="summary-value" id="isummDesc">—</span>
              </div>

              <div class="summary-divider"></div>

              <div class="summary-total">
                <span class="summary-total-label">Amount</span>
                <span class="summary-total-value" id="isummAmount">$0.00</span>
              </div>

              <div class="summary-note">
                ⏳ International wire transfers are subject to compliance review and typically process within 1–3
                business days. Your balance will be reserved immediately.
              </div>
            </div>

          </div>
        </div>

      </main>
    </div>
  </div>

  <!-- Success Modal -->
  <div class="modal-overlay" id="successModal">
    <div class="modal">
      <div class="modal-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <h2 id="modalTitle">Transfer Successful</h2>
      <p id="modalMessage">Your transfer has been processed successfully.</p>
      <div class="modal-ref" id="modalRef">REF: —</div>
      <div class="modal-pending-badge" id="modalPending" style="display:none">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        Pending Review
      </div>
      <button class="modal-btn" onclick="closeModal()">Done</button>
      <button class="modal-btn-outline" onclick="Utils.navigateTo('transactions.html')">View Transactions</button>
    </div>
  </div>

  <script src="../../assets/js/api.js"></script>
  <script src="../../assets/js/auth.js"></script>
  <script src="../../assets/js/utils.js"></script>
  <script src="../../assets/js/timeUtils.js"></script>
  <script src="../../assets/js/receiptModal.js"></script>
  <script>
    (async () => {
      const authenticated = await Auth.requireAuthAsync();
      if (!authenticated) return;
      renderCountries();
      await init();
    })();

    let currentBalance = 0;
    let verifiedRecipient = null;
    let currentTab = 'local';
    let verifyTimeout = null;

    const countries = [
      "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
      "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
      "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
      "Denmark", "Djibouti", "Dominica", "Dominican Republic",
      "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
      "Fiji", "Finland", "France",
      "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
      "Haiti", "Honduras", "Hungary",
      "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
      "Jamaica", "Japan", "Jordan",
      "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan",
      "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
      "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
      "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
      "Oman",
      "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
      "Qatar",
      "Romania", "Russia", "Rwanda",
      "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
      "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
      "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
      "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
      "Yemen",
      "Zambia", "Zimbabwe"
    ];

    function renderCountries(list = countries) {
      const container = document.getElementById('countryList');
      container.innerHTML = list.map(c => `<div class="search-option" onclick="selectCountry('${c.replace(/'/g, "\\'")}')">${c}</div>`).join('');
    }

    function toggleCountrySelect() {
      document.getElementById('countrySelect').classList.toggle('open');
    }

    function filterCountries(val) {
      const filtered = countries.filter(c => c.toLowerCase().includes(val.toLowerCase()));
      renderCountries(filtered);
    }

    function selectCountry(val) {
      document.getElementById('selectedCountry').textContent = val;
      document.getElementById('countrySelect').classList.remove('open');
      hideFieldError('error_intlCountry');
      updateIntlSummary();
    }

    // Close dropdown on click outside
    window.addEventListener('click', e => {
      if (!e.target.closest('#countrySelect')) {
        document.getElementById('countrySelect').classList.remove('open');
      }
    });

    // ── Init ──
    async function init() {
      const user = Api.getUser();
      if (!user) { Auth.logout(); return; }

      const initials = Auth.getInitials(user.first_name, user.last_name);
      const sA = document.getElementById('sidebarAvatar'); if(sA) sA.textContent = initials;
      const tA = document.getElementById('topbarAvatar'); if(tA) tA.textContent = initials;
      document.getElementById('sidebarName').textContent = `${user.first_name} ${user.last_name}`;
      document.getElementById('summFromName').textContent = `${user.first_name} ${user.last_name}`;

      // Fetch account
      const res = await Api.get('/api/auth/me', true);
      if (res && res.ok && res.data.account) {
        currentBalance = parseFloat(res.data.account.balance);
        document.getElementById('availableBalance').textContent = fmt(currentBalance);
        document.getElementById('summFromAcc').textContent =
          `****${res.data.account.account_number.slice(-4)}`;
      }

      // Check URL param for tab
      const params = new URLSearchParams(window.location.search);
      if (params.get('type') === 'international') switchTab('international');

      setupPinInputs('l');
      setupPinInputs('i');
      updateNotificationDot();
      
      // Initialize receipt modal component
      ReceiptModal.init();
    }

    function setupPinInputs(prefix) {
      const ids = [`${prefix}pin1`, `${prefix}pin2`, `${prefix}pin3`, `${prefix}pin4`];
      ids.forEach((id, i) => {
        const el = document.getElementById(id);
        if (!el) return;

        // Only numbers
        el.addEventListener('keypress', e => {
          if (e.key < '0' || e.key > '9') e.preventDefault();
        });

        el.addEventListener('input', function () {
          this.value = this.value.replace(/[^0-9]/g, '');
          if (this.value && i < 3) document.getElementById(ids[i + 1]).focus();
        });

        el.addEventListener('keydown', function (e) {
          if (e.key === 'Backspace' && !this.value && i > 0) {
            document.getElementById(ids[i - 1]).focus();
          }
        });

        el.addEventListener('paste', e => {
          e.preventDefault();
          const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '');
          if (!paste) return;
          paste.split('').forEach((char, idx) => {
            if (i + idx < 4) {
              const target = document.getElementById(ids[i + idx]);
              target.value = char;
              if (i + idx < 3) document.getElementById(ids[i + idx + 1]).focus();
            }
          });
        });
      });
    }

    function getPin(prefix) {
      return ['pin1', 'pin2', 'pin3', 'pin4']
        .map(id => document.getElementById(`${prefix}${id}`).value)
        .join('');
    }

    function clearPin(prefix) {
      ['pin1', 'pin2', 'pin3', 'pin4'].forEach(id => {
        document.getElementById(`${prefix}${id}`).value = '';
      });
    }

    function fmt(n) {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0);
    }

    // ── Tab switch ──
    function switchTab(tab) {
      currentTab = tab;
      hideAllErrors();

      document.getElementById('panelLocal').classList.toggle('active', tab === 'local');
      document.getElementById('panelIntl').classList.toggle('active', tab === 'international');
      document.getElementById('tabLocal').classList.toggle('active', tab === 'local');
      document.getElementById('tabIntl').classList.toggle('active', tab === 'international');
    }

    // ── Alert ──
    function showAlert(msg) {
      const alert = document.getElementById('formAlert');
      document.getElementById('alertText').textContent = msg;
      alert.classList.add('show');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function hideAlert() {
      document.getElementById('formAlert').classList.remove('show');
    }

    // ── Field Errors ──
    function showFieldError(id, msg) {
      const err = document.getElementById(id);
      if (err) {
        err.textContent = msg;
        err.classList.add('show');
        const inputId = id.replace('error_', '');
        const input = document.getElementById(inputId) || (inputId === 'intlCountry' ? document.getElementById('countrySelect') : null);
        if (input) input.classList.add('error-field');
      }
    }

    function hideFieldError(id) {
      const err = document.getElementById(id);
      if (err) {
        err.classList.remove('show');
        const inputId = id.replace('error_', '');
        const input = document.getElementById(inputId) || (inputId === 'intlCountry' ? document.getElementById('countrySelect') : null);
        if (input) input.classList.remove('error-field');
      }
    }

    function hideAllErrors() {
      hideAlert();
      document.querySelectorAll('.field-error').forEach(el => el.classList.remove('show'));
      document.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
    }

    function setLoading(btnId, dotsId, loading) {
      const btn = document.getElementById(btnId);
      const dots = document.getElementById(dotsId);
      if (!btn) return;
      btn.disabled = loading;
      const text = btn.querySelector('.btn-text');
      const ldr = btn.querySelector('.dot-loader');
      if (text) text.style.display = loading ? 'none' : 'inline';
      if (ldr) ldr.style.display = loading ? 'flex' : 'none';
      if (loading) btn.classList.add('loading');
      else btn.classList.remove('loading');
    }

    // ── Local verify ──
    function onAccNumberInput() {
      const val = document.getElementById('localAccNumber').value.trim();
      hideFieldError('error_localAccNumber');
      document.getElementById('verifiedBadge').classList.remove('show');
      verifiedRecipient = null;
      document.getElementById('summToName').textContent = '—';
      document.getElementById('summToAcc').textContent = '—';

      if (verifyTimeout) clearTimeout(verifyTimeout);
      if (val.length === 10) {
        verifyTimeout = setTimeout(verifyAccount, 500);
      }
      updateSummary();
    }

    async function verifyAccount() {
      const accNum = document.getElementById('localAccNumber').value.trim();
      if (accNum.length !== 10) return;

      document.getElementById('verifyingDots').classList.add('show');
      const res = await Api.get(`/api/transfers/verify-account/${accNum}`, true);
      document.getElementById('verifyingDots').classList.remove('show');

      if (res && res.ok) {
        verifiedRecipient = res.data;
        document.getElementById('verifiedName').textContent = res.data.account_name;
        document.getElementById('verifiedBadge').classList.add('show');
        document.getElementById('summToName').textContent = res.data.account_name;
        document.getElementById('summToAcc').textContent = `****${accNum.slice(-4)}`;
      } else {
        showFieldError('error_localAccNumber', res?.data?.detail || 'Account not found.');
      }
    }

    function updateSummary() {
      const amount = parseFloat(document.getElementById('localAmount').value) || 0;
      const desc = document.getElementById('localDesc').value.trim();
      document.getElementById('summAmount').textContent = fmt(amount);
      document.getElementById('summDesc').textContent = desc || '—';
    }

    function updateIntlSummary() {
      const name = document.getElementById('intlName').value.trim();
      const bank = document.getElementById('intlBank').value.trim();
      const country = document.getElementById('selectedCountry').textContent.trim();
      const desc = document.getElementById('intlDesc').value.trim();
      const amount = parseFloat(document.getElementById('intlAmount').value) || 0;

      document.getElementById('isummName').textContent = name || '—';
      document.getElementById('isummBank').textContent = bank || '—';
      document.getElementById('isummCountry').textContent = country === 'Select Country' ? '—' : country;
      document.getElementById('isummDesc').textContent = desc || '—';
      document.getElementById('isummAmount').textContent = fmt(amount);
    }

    function checkCodeRequirement() {
      const amount = parseFloat(document.getElementById('intlAmount').value) || 0;
      const show = amount >= 10000;
      document.getElementById('codeInfoBox').classList.toggle('show', show);
      document.getElementById('cotField').style.display = show ? 'block' : 'none';
      document.getElementById('bopField').style.display = show ? 'block' : 'none';
    }

    async function submitLocalTransfer() {
      hideAllErrors();
      const accNum = document.getElementById('localAccNumber').value.trim();
      const amountInput = document.getElementById('localAmount');
      const amount = parseFloat(amountInput.value);
      const pin = getPin('l');

      let valid = true;
      if (!accNum) { showFieldError('error_localAccNumber', 'Account required.'); valid = false; }
      else if (!verifiedRecipient) { showFieldError('error_localAccNumber', 'Verify account first.'); valid = false; }
      if (!amountInput.value) { showFieldError('error_localAmount', 'Amount required.'); valid = false; }
      else if (amount <= 0) { showFieldError('error_localAmount', 'Invalid amount.'); valid = false; }
      else if (amount > currentBalance) { showFieldError('error_localAmount', 'Insufficient balance.'); valid = false; }
      if (pin.length !== 4) { showFieldError('error_localPin', '4-digit PIN required.'); valid = false; }

      if (!valid) return;

      setLoading('localSubmitBtn', 'localDots', true);
      const res = await Api.post('/api/transfers/local', {
        recipient_account_number: accNum,
        amount, description: document.getElementById('localDesc').value.trim() || null, pin
      }, true);
      setLoading('localSubmitBtn', 'localDots', false);
      clearPin('l');

      if (res && res.ok) {
        currentBalance = res.data.new_balance;
        document.getElementById('availableBalance').textContent = fmt(currentBalance);
        showModal('Transfer Successful', `Sent ${fmt(amount)} to ${verifiedRecipient.account_name}.`, res.data.reference, false);
        document.getElementById('localAccNumber').value = '';
        amountInput.value = '';
        document.getElementById('verifiedBadge').classList.remove('show');
        verifiedRecipient = null;
        updateSummary();
        updateNotificationDot();
      } else {
        showAlert(res?.data?.detail || 'Transaction failed.');
      }
    }
    async function submitIntlTransfer() {
      hideAllErrors();

      const name = document.getElementById('intlName').value.trim();
      const bank = document.getElementById('intlBank').value.trim();
      const account = document.getElementById('intlAccount').value.trim();
      const swift = document.getElementById('intlSwift').value.trim();
      const country = document.getElementById('selectedCountry').textContent.trim();
      const amount = parseFloat(document.getElementById('intlAmount').value);
      const desc = document.getElementById('intlDesc').value.trim();
      const pin = getPin('i');

      let valid = true;
      if (!name) { showFieldError('error_intlName', 'Recipient name is required.'); valid = false; }
      if (!bank) { showFieldError('error_intlBank', 'Bank name is required.'); valid = false; }
      if (country === 'Select Country') { showFieldError('error_intlCountry', 'Select a country.'); valid = false; }
      if (!account) { showFieldError('error_intlAccount', 'Account/IBAN is required.'); valid = false; }
      if (!swift) { showFieldError('error_intlSwift', 'SWIFT/BIC is required.'); valid = false; }
      if (!amount || amount < 10) { showFieldError('error_intlAmount', 'Min amount $10.00.'); valid = false; }
      else if (amount > currentBalance) { showFieldError('error_intlAmount', 'Insufficient balance.'); valid = false; }
      if (!desc) { showFieldError('error_intlDesc', 'Description is required.'); valid = false; }
      if (pin.length !== 4) { showFieldError('error_intlPin', '4-digit PIN required.'); valid = false; }

      if (!valid) return;

      setLoading('intlSubmitBtn', 'intlDots', true);
      const res = await Api.post('/api/transfers/international', {
        recipient_name: name, recipient_bank: bank,
        recipient_bank_address: document.getElementById('intlBankAddress').value.trim() || null,
        recipient_account: account, recipient_swift: swift, recipient_country: country,
        recipient_routing: document.getElementById('intlRouting').value.trim() || null,
        amount, description: desc, pin,
        cot_code: document.getElementById('cotCode').value.trim() || null,
        bop_code: document.getElementById('bopCode').value.trim() || null
      }, true);

      setLoading('intlSubmitBtn', 'intlDots', false);
      clearPin('i');

      if (res && res.ok) {
        currentBalance = res.data.new_balance;
        document.getElementById('availableBalance').textContent = fmt(currentBalance);
        showModal('Wire Submitted', `Wire of ${fmt(amount)} to ${name} is processing.`, res.data.reference, true);
        updateNotificationDot();
      } else {
        showAlert(res?.data?.detail || 'Wire failed. Please try again.');
      }
    }

    // ── Modal ──
    function showModal(title, message, ref, isPending) {
      document.getElementById('modalTitle').textContent = title;
      document.getElementById('modalMessage').textContent = message;
      document.getElementById('modalRef').textContent = `REF: ${ref}`;
      document.getElementById('modalPending').style.display = isPending ? 'flex' : 'none';
      document.getElementById('successModal').classList.add('show');
    }

    function closeModal() {
      document.getElementById('successModal').classList.remove('show');
    }

    // ── Mobile sidebar ──
    function openSidebar() {
      document.getElementById('sidebar').classList.add('open');
      document.getElementById('sidebarOverlay').classList.add('show');
      document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
      document.getElementById('sidebar').classList.remove('open');
      document.getElementById('sidebarOverlay').classList.remove('show');
      document.body.style.overflow = '';
    }

    function nav(e, path) {
      if (e) e.preventDefault();
      closeSidebar();
      Utils.navigateTo(path);
    }

    // Update notification dot
    async function updateNotificationDot() {
      try {
        const res = await Api.get('/api/notifications/unread-count', true);
        if (res && res.ok) {
          const data = res.data;
          const notifDot = document.getElementById('notifDot');
          if (data.count > 0) {
            notifDot.style.display = 'flex';
            notifDot.textContent = data.count > 99 ? '99+' : data.count;
          } else {
            notifDot.style.display = 'none';
          }
        }
      } catch (err) {
        console.error('Error updating notification dot:', err);
      }
    }

    // Mark single notification as read
    async function markNotificationAsRead(notifId) {
      try {
        const res = await Api.post(`/api/notifications/${notifId}/mark-read`, {}, true);
        if (res && res.ok) {
          updateNotificationDot();
        }
      } catch (err) {
        console.error('Error marking notification as read:', err);
      }
    }

    // Open receipt modal from notification
    async function openNotificationReceipt(notifId) {
      try {
        const res = await Api.get(`/api/notifications/${notifId}`, true);
        if (res && res.ok) {
          const notif = res.data;
          // If it's a transaction notification, populate and show receipt modal
          if (notif.type === 'transaction' && notif.data) {
            const isSent = notif.title.toLowerCase().includes('sent');
            ReceiptModal.open({
              amount: notif.data.amount,
              partyLabel: isSent ? 'Transfer To' : 'Transfer From',
              party: notif.data.recipient || notif.data.sender || 'Unknown',
              reference: notif.data.reference || '#000000',
              bank: 'Arcteron Trust',
              recipientAccount: notif.data.recipient_account || '0000',
              date: TimeUtils.formatDateTime(notif.created_at).split(' at ')[0],
              time: TimeUtils.formatDateTime(notif.created_at).split(' at ')[1],
              type: isSent ? 'Transfer Sent' : 'Transfer Received',
              account: '0000',
              status: 'Completed',
              isCredit: !isSent
            });
          }
        }
      } catch (err) {
        console.error('Error opening notification receipt:', err);
      }
    }

    // init() is now called by the async IIFE at the top

  </script>

  <script>
    function closeReceiptModal() {
      ReceiptModal.close();
    }
  </script>
</body>

</html>
```

---

### FRONTEND 9: set-pin.html
File Path: `frontend/pages/set-pin.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Set transaction PIN — Arcteron Trust</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/theme.css">
  <link rel="stylesheet" href="../assets/css/style.css">
  <script src="../assets/js/theme.js"></script>
  <style>
    body { font-family: 'DM Sans', sans-serif; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-primary); padding: 24px; }
    .card {
      width: 100%; max-width: 400px;
      background: var(--bg-secondary);
      border: 1.5px solid var(--border-color);
      border-radius: 14px;
      padding: 32px 28px;
      box-shadow: var(--shadow-md);
      position: relative;
    }
    .theme-wrap { position: absolute; top: 16px; right: 16px; }
    .theme-btn {
      width: 34px; height: 34px; border-radius: 8px;
      background: var(--bg-primary); border: 1.5px solid var(--border-color);
      color: var(--text-secondary); display: flex; align-items: center; justify-content: center;
      cursor: pointer;
    }
    h1 { font-family: 'Cormorant Garamond', serif; font-size: 26px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
    .sub { font-size: 14px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.5; }
    label { display: block; font-size: 11px; font-weight: 600; letter-spacing: 0.8px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
    input.pin-field {
      width: 100%; background: var(--bg-primary); border: 1.5px solid var(--border-color);
      border-radius: 8px; padding: 14px 16px; font-size: 18px; letter-spacing: 8px; text-align: center;
      color: var(--text-primary); font-family: 'DM Sans', sans-serif; margin-bottom: 18px;
    }
    .submit-btn {
      width: 100%; background: #111827; color: #fff; border: none; border-radius: 8px;
      padding: 14px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: 'DM Sans', sans-serif;
    }
    [data-theme="dark"] .submit-btn { background: #E5E7EB; color: #0F1115; }
    [data-theme="dark"] .card { background: #171A20; border-color: #2B2F36; }
    [data-theme="dark"] input.pin-field { background: #0F1115; border-color: #2B2F36; color: #E5E7EB; }
    [data-theme="dark"] h1 { color: #E5E7EB; }
    .form-alert { display: none; padding: 12px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; border-left: 3px solid #EF4444; background: rgba(239,68,68,0.08); color: #DC2626; }
    [data-theme="dark"] .form-alert { color: #FCA5A5; background: rgba(239,68,68,0.12); }
    .form-alert.show { display: block; }
  </style>
</head>
<body>
  <div class="card">
    <div class="theme-wrap">
      <button type="button" class="theme-btn" onclick="Theme.toggle()" title="Toggle theme">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      </button>
    </div>
    <h1>Create transaction PIN</h1>
    <p class="sub">Choose a 4-digit PIN. You will enter it each time you sign in before accessing your account.</p>
    <div id="formAlert" class="form-alert"></div>
    <label for="pin1">PIN</label>
    <input class="pin-field" id="pin1" type="password" maxlength="4" inputmode="numeric" autocomplete="new-password" placeholder="••••">
    <label for="pin2">Confirm PIN</label>
    <input class="pin-field" id="pin2" type="password" maxlength="4" inputmode="numeric" autocomplete="new-password" placeholder="••••">
    <button type="button" class="submit-btn" id="btnSubmit" onclick="submitSetPin()">Save PIN &amp; continue</button>
  </div>
  <script src="../assets/js/api.js"></script>
  <script src="../assets/js/auth.js"></script>
  <script src="../assets/js/utils.js"></script>
  <script>
    (async function gate() {
      if (!Api.getToken()) {
        window.location.href = '/frontend/pages/login.html';
        return;
      }
      let user = Api.getUser();
      if (!user) {
        Auth.logout();
        return;
      }
      if (typeof user.has_pin !== 'boolean') {
        const res = await Api.get('/api/auth/me', true);
        if (!res || !res.ok) {
          Auth.logout();
          return;
        }
        Api.setUser(res.data);
        user = res.data;
      }
      if (user.has_pin === true && Auth.isPinSessionVerified()) {
        Auth.redirectByRole(user);
        return;
      }
      if (user.has_pin === true && !Auth.isPinSessionVerified()) {
        window.location.href = '/frontend/pages/enter-pin.html';
      }
    })();

    function showAlert(msg) {
      const el = document.getElementById('formAlert');
      el.textContent = msg;
      el.classList.add('show');
    }
    function hideAlert() {
      document.getElementById('formAlert').classList.remove('show');
    }

    async function submitSetPin() {
      hideAlert();
      const pin = document.getElementById('pin1').value.trim();
      const confirm = document.getElementById('pin2').value.trim();
      if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
        return showAlert('PIN must be exactly 4 digits.');
      }
      if (pin !== confirm) {
        return showAlert('PINs do not match.');
      }
      const btn = document.getElementById('btnSubmit');
      btn.disabled = true;
      const res = await Api.post('/api/auth/pin/set', { pin, confirm_pin: confirm }, true);
      btn.disabled = false;
      if (res && res.ok) {
        const u = Api.getUser();
        Api.setUser({ ...u, has_pin: true });
        Auth.markPinSessionVerified();
        Auth.redirectByRole(Api.getUser());
      } else {
        const detail = res?.data?.detail;
        showAlert(Array.isArray(detail) ? detail.map(d => d.msg).join(' ') : (detail || 'Could not save PIN. Try again.'));
      }
    }
  </script>
</body>
</html>
```

---

### FRONTEND 10: enter-pin.html
File Path: `frontend/pages/enter-pin.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enter PIN — Arcteron Trust</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/theme.css">
  <link rel="stylesheet" href="../assets/css/style.css">
  <script src="../assets/js/theme.js"></script>
  <style>
    body { font-family: 'DM Sans', sans-serif; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-primary); padding: 24px; }
    .card {
      width: 100%; max-width: 400px;
      background: var(--bg-secondary);
      border: 1.5px solid var(--border-color);
      border-radius: 14px;
      padding: 32px 28px;
      box-shadow: var(--shadow-md);
      position: relative;
    }
    .theme-wrap { position: absolute; top: 16px; right: 16px; }
    .theme-btn {
      width: 34px; height: 34px; border-radius: 8px;
      background: var(--bg-primary); border: 1.5px solid var(--border-color);
      color: var(--text-secondary); display: flex; align-items: center; justify-content: center;
      cursor: pointer;
    }
    h1 { font-family: 'Cormorant Garamond', serif; font-size: 26px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
    .sub { font-size: 14px; color: var(--text-secondary); margin-bottom: 20px; }
    .user-preview { text-align: center; margin-bottom: 20px; }
    .user-preview-avatar {
      width: 56px; height: 56px; border-radius: 50%; background: #111827; color: #fff;
      display: inline-flex; align-items: center; justify-content: center;
      font-family: 'Cormorant Garamond', serif; font-size: 20px; font-weight: 600;
      border: 3px solid var(--border-color); margin-bottom: 8px;
    }
    [data-theme="dark"] .user-preview-avatar { background: #E5E7EB; color: #111827; }
    .user-preview-name { font-size: 15px; font-weight: 600; color: var(--text-primary); }
    .user-preview-email { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
    .pin-inputs { display: flex; gap: 10px; justify-content: center; margin: 20px 0; }
    .pin-digit {
      width: 48px; height: 52px; border: 1.5px solid var(--border-color); border-radius: 10px;
      background: var(--bg-primary); font-size: 20px; font-weight: 700; text-align: center;
      color: var(--text-primary); font-family: 'DM Sans', sans-serif;
    }
    [data-theme="dark"] .pin-digit { background: #0F1115; border-color: #2B2F36; color: #E5E7EB; }
    .submit-btn {
      width: 100%; background: #111827; color: #fff; border: none; border-radius: 8px;
      padding: 14px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: 'DM Sans', sans-serif;
    }
    [data-theme="dark"] .submit-btn { background: #E5E7EB; color: #0F1115; }
    [data-theme="dark"] .card { background: #171A20; border-color: #2B2F36; }
    [data-theme="dark"] h1 { color: #E5E7EB; }
    .form-alert { display: none; padding: 12px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; border-left: 3px solid #EF4444; background: rgba(239,68,68,0.08); color: #DC2626; }
    [data-theme="dark"] .form-alert { color: #FCA5A5; background: rgba(239,68,68,0.12); }
    .form-alert.show { display: block; }
    .footer-links { margin-top: 16px; text-align: center; font-size: 13px; }
    .footer-links a { color: var(--text-secondary); font-weight: 500; transition: color 0.2s; }
    .footer-links a:hover { color: var(--text-primary); }
  </style>
</head>
<body>
  <div class="card">
    <div class="theme-wrap">
      <button type="button" class="theme-btn" onclick="Theme.toggle()" title="Toggle theme">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      </button>
    </div>
    <h1>Enter your PIN</h1>
    <p class="sub">4-digit transaction PIN to continue to your account.</p>
    <div id="formAlert" class="form-alert"></div>
    <div class="user-preview">
      <div class="user-preview-avatar" id="previewAvatar">—</div>
      <div class="user-preview-name" id="previewName">…</div>
      <div class="user-preview-email" id="previewEmail">…</div>
    </div>
    <div class="pin-inputs">
      <input class="pin-digit" id="pin1" type="password" maxlength="1" inputmode="numeric">
      <input class="pin-digit" id="pin2" type="password" maxlength="1" inputmode="numeric">
      <input class="pin-digit" id="pin3" type="password" maxlength="1" inputmode="numeric">
      <input class="pin-digit" id="pin4" type="password" maxlength="1" inputmode="numeric">
    </div>
    <button type="button" class="submit-btn" id="btnSubmit" onclick="submitPin()">Continue</button>
    <div class="footer-links">
      <a href="#" onclick="Auth.logout(); return false;">Use a different account</a>
      &nbsp;·&nbsp;
      <a href="/frontend/pages/forgot-pin.html">Forgot PIN?</a>
    </div>
  </div>
  <script src="../assets/js/api.js"></script>
  <script src="../assets/js/auth.js"></script>
  <script src="../assets/js/utils.js"></script>
  <script>
    const pinIds = ['pin1', 'pin2', 'pin3', 'pin4'];

    (async function gate() {
      if (!Api.getToken()) {
        window.location.href = '/frontend/pages/login.html';
        return;
      }
      let user = Api.getUser();
      if (!user) {
        Auth.logout();
        return;
      }
      if (typeof user.has_pin !== 'boolean') {
        const res = await Api.get('/api/auth/me', true);
        if (!res || !res.ok) {
          Auth.logout();
          return;
        }
        Api.setUser(res.data);
        user = res.data;
      }
      if (user.has_pin === false) {
        window.location.href = '/frontend/pages/set-pin.html';
        return;
      }
      if (Auth.isPinSessionVerified()) {
        Auth.redirectByRole(user);
        return;
      }

      const initials = Auth.getInitials(user.first_name, user.last_name);
      document.getElementById('previewAvatar').textContent = initials;
      document.getElementById('previewName').textContent = `${user.first_name} ${user.last_name}`;
      document.getElementById('previewEmail').textContent = user.email;
    })();

    pinIds.forEach((id, i) => {
      const el = document.getElementById(id);
      el.addEventListener('input', function() {
        if (this.value && i < 3) document.getElementById(pinIds[i + 1]).focus();
        if (this.value && i === 3) submitPin();
      });
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && !this.value && i > 0) {
          document.getElementById(pinIds[i - 1]).focus();
        }
      });
    });

    function showAlert(msg) {
      const el = document.getElementById('formAlert');
      el.textContent = msg;
      el.classList.add('show');
    }
    function hideAlert() {
      document.getElementById('formAlert').classList.remove('show');
    }

    async function submitPin() {
      hideAlert();
      const pin = pinIds.map(id => document.getElementById(id).value).join('');
      if (pin.length !== 4) {
        return showAlert('Please enter your 4-digit PIN.');
      }
      const btn = document.getElementById('btnSubmit');
      btn.disabled = true;
      const res = await Api.post('/api/auth/verify-pin', { pin }, true);
      btn.disabled = false;
      if (res && res.ok) {
        Auth.markPinSessionVerified();
        Auth.redirectByRole(Api.getUser());
      } else {
        pinIds.forEach(id => { document.getElementById(id).value = ''; });
        document.getElementById('pin1').focus();
        const detail = res?.data?.detail;
        showAlert(typeof detail === 'string' ? detail : 'Incorrect PIN. Try again.');
      }
    }
  </script>
</body>
</html>
```

---

### FRONTEND 11: verify-email.html
File Path: `frontend/pages/verify-email.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Email — Arcteron Trust</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../assets/css/theme.css">
    <link rel="stylesheet" href="../assets/css/style.css">
    <script src="../assets/js/theme.js"></script>
    <style>
        body {
            font-family: 'DM Sans', sans-serif;
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-primary);
        }

        .verification-container {
            width: 100%;
            max-width: 420px;
            padding: 40px;
            background: var(--bg-secondary);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-lg);
        }

        .logo-section {
            text-align: center;
            margin-bottom: 32px;
        }

        .logo-svg {
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
        }

        .logo-section h1 {
            font-family: 'Cormorant Garamond', serif;
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0 0 8px 0;
        }

        .logo-section p {
            font-size: 12px;
            color: var(--text-muted);
            margin: 0;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .status-message {
            text-align: center;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }

        .status-message.success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: #10B981;
        }

        .status-message.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #EF4444;
        }

        .status-message.loading {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            color: #3B82F6;
        }

        .status-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }

        .status-text {
            font-size: 15px;
            font-weight: 500;
            margin-bottom: 8px;
        }

        .status-subtext {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .action-button {
            width: 100%;
            padding: 14px 24px;
            background: var(--text-primary);
            color: var(--bg-primary);
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .action-button:hover {
            opacity: 0.85;
        }

        .action-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .resend-link {
            text-align: center;
            margin-top: 20px;
        }

        .resend-link a {
            color: var(--text-secondary);
            font-size: 13px;
            text-decoration: none;
        }

        .resend-link a:hover {
            color: var(--text-primary);
            text-decoration: underline;
        }

        @media (max-width: 480px) {
            .verification-container {
                padding: 24px;
                margin: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="verification-container">
        <div class="logo-section">
            <svg class="logo-svg" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
                <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                <path d="M14 23 H26" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
                <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.5" />
            </svg>
            <h1>Arcteron Trust</h1>
            <p>Private Banking & Wealth Management</p>
        </div>

        <div id="statusMessage" class="status-message loading">
            <div class="status-icon">⏳</div>
            <div class="status-text">Verifying your email...</div>
            <div class="status-subtext">Please wait while we process your verification</div>
        </div>

        <div id="actionSection" style="display: none;">
            <button id="actionButton" class="action-button" onclick="handleAction()">Continue to Login</button>
            <div class="resend-link">
                <a href="resend-verification.html">Didn't receive the email? Request a new one</a>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'https://arcteron-trust.onrender.com';

        async function verifyEmail() {
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get('token');

            if (!token) {
                showError('Invalid verification link. No token provided.');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/api/auth/email-verification/confirm`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ token: token })
                });

                const data = await response.json();

                if (response.ok) {
                    showSuccess(data.message);
                } else {
                    showError(data.detail || 'Verification failed. Please try again.');
                }
            } catch (error) {
                showError('Network error. Please check your connection and try again.');
            }
        }

        function showSuccess(message) {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.className = 'status-message success';
            statusMessage.innerHTML = `
                <div class="status-icon">✓</div>
                <div class="status-text">${message}</div>
                <div class="status-subtext">Your email has been verified successfully</div>
            `;

            const actionSection = document.getElementById('actionSection');
            actionSection.style.display = 'block';
        }

        function showError(message) {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.className = 'status-message error';
            statusMessage.innerHTML = `
                <div class="status-icon">✕</div>
                <div class="status-text">Verification Failed</div>
                <div class="status-subtext">${message}</div>
            `;

            const actionSection = document.getElementById('actionSection');
            actionSection.style.display = 'block';

            const actionButton = document.getElementById('actionButton');
            actionButton.textContent = 'Request New Verification Email';
            actionButton.onclick = () => window.location.href = 'resend-verification.html';
        }

        function handleAction() {
            window.location.href = 'login.html';
        }

        // Auto-verify on page load
        window.addEventListener('DOMContentLoaded', verifyEmail);
    </script>
</body>
</html>
```

---

### FRONTEND 12: index.html
File Path: `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arcteron Trust — Private Banking & Wealth Management, Boston MA</title>
    <meta name="description"
        content="Arcteron Trust offers private banking, wealth management, and business banking services in Boston, MA. FDIC insured. Open an account today.">
    <link rel="icon" type="image/svg+xml" href="/frontend/assets/images/logo.svg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link
        href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=DM+Sans:wght@300;400;500;600&display=swap"
        rel="stylesheet">
    <link rel="stylesheet" href="/frontend/assets/css/theme.css">
    <link rel="stylesheet" href="/frontend/assets/css/style.css">
    <link rel="stylesheet" href="/frontend/assets/css/public.css">
    <script src="/frontend/assets/js/theme.js"></script>
</head>

<body class="public-page">

    <!-- ═══════════════════════════════════════════════
     NEWS TICKER BAR
══════════════════════════════════════════════════ -->
    <div class="news-ticker-bar" role="marquee" aria-live="off">
        <div class="ticker-label">
            <div class="ticker-dot"></div>
            LIVE
        </div>
        <div class="ticker-track-wrap">
            <div class="ticker-track" id="tickerTrack"></div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════════
     NAVIGATION
══════════════════════════════════════════════════ -->
    <nav class="pub-nav" role="navigation" aria-label="Main navigation">
        <div class="nav-inner">
            <!-- Brand -->
            <a href="/frontend/index.html" class="nav-brand">
                <svg class="nav-brand-logo" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
                    <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                    <path d="M14 23 H26" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
                    <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.5" />
                </svg>
                <div class="nav-brand-text">
                    <span class="nav-brand-name">Arcteron Trust</span>
                    <span class="nav-brand-sub">Private Banking</span>
                </div>
            </a>

            <!-- Desktop Links -->
            <ul class="nav-links">
                <li>
                    <button class="nav-link-btn" aria-haspopup="true">
                        Personal Banking
                        <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                    <div class="nav-dropdown">
                        <a href="/frontend/pages/personal-banking.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="2" y="5" width="20" height="14" rx="2" />
                                <line x1="2" y1="10" x2="22" y2="10" />
                            </svg>
                            Checking Accounts
                        </a>
                        <a href="/frontend/pages/personal-banking.html#savings">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
                                <path d="M12 6v6l4 2" />
                            </svg>
                            Savings Accounts
                        </a>
                        <a href="/frontend/pages/personal-banking.html#credit">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                                <line x1="1" y1="10" x2="23" y2="10" />
                            </svg>
                            Credit Cards
                        </a>
                        <div class="nav-dropdown-divider"></div>
                        <a href="/frontend/pages/login.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                                <polyline points="10 17 15 12 10 7" />
                                <line x1="15" y1="12" x2="3" y2="12" />
                            </svg>
                            Online Banking Login
                        </a>
                    </div>
                </li>
                <li>
                    <button class="nav-link-btn" aria-haspopup="true">
                        Business Banking
                        <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                    <div class="nav-dropdown">
                        <a href="/frontend/pages/business-banking.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            </svg>
                            Business Checking
                        </a>
                        <a href="/frontend/pages/business-banking.html#merchant">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="1" x2="12" y2="23" />
                                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                            </svg>
                            Merchant Services
                        </a>
                        <a href="/frontend/pages/business-banking.html#loans">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>
                            Business Loans
                        </a>
                        <div class="nav-dropdown-divider"></div>
                        <a href="/frontend/pages/business-banking.html#treasury">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path
                                    d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                            </svg>
                            Treasury Management
                        </a>
                    </div>
                </li>
                <li>
                    <button class="nav-link-btn" aria-haspopup="true">
                        Wealth Management
                        <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                    <div class="nav-dropdown">
                        <a href="/frontend/pages/wealth-management.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>
                            Investment Advisory
                        </a>
                        <a href="/frontend/pages/wealth-management.html#retirement">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10" />
                                <polyline points="12 6 12 12 16 14" />
                            </svg>
                            Retirement Planning
                        </a>
                        <a href="/frontend/pages/wealth-management.html#estate">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            </svg>
                            Estate Planning
                        </a>
                        <div class="nav-dropdown-divider"></div>
                        <a href="/frontend/pages/wealth-management.html#trust">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            Trust Services
                        </a>
                    </div>
                </li>
                <li>
                    <button class="nav-link-btn" aria-haspopup="true">
                        Loans
                        <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                    <div class="nav-dropdown">
                        <a href="/frontend/pages/loans.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            </svg>
                            Home Loans
                        </a>
                        <a href="/frontend/pages/loans.html#auto">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="1" y="3" width="15" height="13" rx="2" />
                                <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
                                <circle cx="5.5" cy="18.5" r="2.5" />
                                <circle cx="18.5" cy="18.5" r="2.5" />
                            </svg>
                            Auto Loans
                        </a>
                        <a href="/frontend/pages/loans.html#personal">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                <circle cx="12" cy="7" r="4" />
                            </svg>
                            Personal Loans
                        </a>
                        <a href="/frontend/pages/loans.html#student">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                                <path d="M6 12v5c3 3 9 3 12 0v-5" />
                            </svg>
                            Student Loans
                        </a>
                    </div>
                </li>
                <li>
                    <button class="nav-link-btn" aria-haspopup="true">
                        About Us
                        <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>
                    <div class="nav-dropdown">
                        <a href="/frontend/pages/about.html">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="12" y1="8" x2="12" y2="12" />
                                <line x1="12" y1="16" x2="12.01" y2="16" />
                            </svg>
                            Our Story
                        </a>
                        <a href="/frontend/pages/about.html#leadership">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                                <circle cx="9" cy="7" r="4" />
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                            </svg>
                            Leadership Team
                        </a>
                        <a href="/frontend/pages/about.html#community">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            </svg>
                            Community Impact
                        </a>
                        <a href="/frontend/pages/about.html#careers">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="2" y="7" width="20" height="14" rx="2" />
                                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                            </svg>
                            Careers
                        </a>
                    </div>
                </li>
                <li>
                    <a href="/frontend/pages/contact.html" class="nav-link-btn">Contact</a>
                </li>
            </ul>

            <!-- Actions -->
            <div class="nav-actions">
                <a href="/frontend/pages/login.html" class="nav-btn-signin">Sign In</a>
                <a href="/frontend/pages/register.html" class="nav-btn-open">Open Account</a>
                <button class="nav-theme-btn" id="themeToggle" aria-label="Toggle theme"></button>
                <button class="nav-hamburger" id="navHamburger" aria-label="Open menu">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="3" y1="6" x2="21" y2="6" />
                        <line x1="3" y1="12" x2="21" y2="12" />
                        <line x1="3" y1="18" x2="21" y2="18" />
                    </svg>
                </button>
            </div>
        </div>
    </nav>

    <!-- Mobile Drawer -->
    <div class="mobile-drawer" id="mobileDrawer">
        <div class="drawer-overlay"></div>
        <div class="drawer-panel">
            <div class="drawer-header">
                <div class="nav-brand">
                    <svg style="width:26px;height:26px;color:var(--text-primary)" viewBox="0 0 40 40" fill="none">
                        <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
                        <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                        <path d="M14 23 H26" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
                    </svg>
                    <span class="nav-brand-name">Arcteron Trust</span>
                </div>
                <button class="drawer-close" id="drawerClose" aria-label="Close menu">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                </button>
            </div>
            <div class="drawer-nav">
                <div class="drawer-nav-section">
                    <button class="drawer-nav-trigger">Personal Banking <svg class="drawer-chevron" viewBox="0 0 24 24"
                            fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg></button>
                    <div class="drawer-sub-links">
                        <a href="/frontend/pages/personal-banking.html"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <rect x="2" y="5" width="20" height="14" rx="2" />
                                <line x1="2" y1="10" x2="22" y2="10" />
                            </svg>Checking Accounts</a>
                        <a href="/frontend/pages/personal-banking.html#savings"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10" />
                            </svg>Savings Accounts</a>
                        <a href="/frontend/pages/personal-banking.html#credit"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <rect x="1" y="4" width="22" height="16" rx="2" />
                            </svg>Credit Cards</a>
                        <a href="/frontend/pages/login.html"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2">
                                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                                <polyline points="10 17 15 12 10 7" />
                            </svg>Online Banking</a>
                    </div>
                </div>
                <div class="drawer-nav-section">
                    <button class="drawer-nav-trigger">Business Banking <svg class="drawer-chevron" viewBox="0 0 24 24"
                            fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg></button>
                    <div class="drawer-sub-links">
                        <a href="/frontend/pages/business-banking.html"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            </svg>Business Checking</a>
                        <a href="/frontend/pages/business-banking.html#merchant"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="1" x2="12" y2="23" />
                                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                            </svg>Merchant Services</a>
                        <a href="/frontend/pages/business-banking.html#loans"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>Business Loans</a>
                        <a href="/frontend/pages/business-banking.html#treasury"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8" />
                            </svg>Treasury Management</a>
                    </div>
                </div>
                <div class="drawer-nav-section">
                    <button class="drawer-nav-trigger">Wealth Management <svg class="drawer-chevron" viewBox="0 0 24 24"
                            fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg></button>
                    <div class="drawer-sub-links">
                        <a href="/frontend/pages/wealth-management.html"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>Investment Advisory</a>
                        <a href="/frontend/pages/wealth-management.html#retirement"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10" />
                            </svg>Retirement Planning</a>
                        <a href="/frontend/pages/wealth-management.html#estate"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11" />
                            </svg>Estate Planning</a>
                        <a href="/frontend/pages/wealth-management.html#trust"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>Trust Services</a>
                    </div>
                </div>
                <div class="drawer-nav-section">
                    <button class="drawer-nav-trigger">Loans <svg class="drawer-chevron" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg></button>
                    <div class="drawer-sub-links">
                        <a href="/frontend/pages/loans.html"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2">
                                <path d="M3 9l9-7 9 7v11" />
                            </svg>Home Loans</a>
                        <a href="/frontend/pages/loans.html#auto"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <rect x="1" y="3" width="15" height="13" rx="2" />
                            </svg>Auto Loans</a>
                        <a href="/frontend/pages/loans.html#personal"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="7" r="4" />
                            </svg>Personal Loans</a>
                        <a href="/frontend/pages/loans.html#student"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                            </svg>Student Loans</a>
                    </div>
                </div>
                <div class="drawer-nav-section">
                    <button class="drawer-nav-trigger">About Us <svg class="drawer-chevron" viewBox="0 0 24 24"
                            fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9" />
                        </svg></button>
                    <div class="drawer-sub-links">
                        <a href="/frontend/pages/about.html"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2">
                                <circle cx="12" cy="12" r="10" />
                            </svg>Our Story</a>
                        <a href="/frontend/pages/about.html#leadership"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5" />
                            </svg>Leadership</a>
                        <a href="/frontend/pages/about.html#community"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <path d="M3 9l9-7 9 7v11" />
                            </svg>Community</a>
                        <a href="/frontend/pages/about.html#careers"><svg viewBox="0 0 24 24" fill="none"
                                stroke="currentColor" stroke-width="2">
                                <rect x="2" y="7" width="20" height="14" rx="2" />
                            </svg>Careers</a>
                    </div>
                </div>
                <a href="/frontend/pages/contact.html" class="drawer-solo-link">Contact</a>
            </div>
            <div class="drawer-footer">
                <a href="/frontend/pages/login.html" class="nav-btn-signin">Sign In</a>
                <a href="/frontend/pages/register.html" class="nav-btn-open">Open Account</a>
            </div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════════
     HERO SLIDESHOW
══════════════════════════════════════════════════ -->
    <section class="hero-section" id="heroSection" aria-label="Hero slideshow">
        <div id="heroSlides"></div>
        <div class="hero-controls">
            <div class="hero-dots" id="heroDots" role="tablist" aria-label="Slide indicators"></div>
            <div class="hero-arrows">
                <button class="hero-arrow" id="heroPrev" aria-label="Previous slide">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 18 9 12 15 6" />
                    </svg>
                </button>
                <button class="hero-arrow" id="heroNext" aria-label="Next slide">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 18 15 12 9 6" />
                    </svg>
                </button>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     TRUST STATS BAR
══════════════════════════════════════════════════ -->
    <div class="stats-bar">
        <div class="stats-bar-inner">
            <div class="stat-bar-item">
                <div class="stat-bar-value" data-count="2.8" data-prefix="$" data-suffix="B+" data-decimals="1">$0B+
                </div>
                <div class="stat-bar-label">Assets Under Management</div>
            </div>
            <div class="stat-bar-item">
                <div class="stat-bar-value" data-count="50" data-suffix="K+">0K+</div>
                <div class="stat-bar-label">Trusted Clients</div>
            </div>
            <div class="stat-bar-item">
                <div class="stat-bar-value" data-count="99.9" data-suffix="%" data-decimals="1">0%</div>
                <div class="stat-bar-label">Platform Uptime</div>
            </div>
            <div class="stat-bar-item">
                <div class="stat-bar-value">FDIC</div>
                <div class="stat-bar-label">Insured · Member FDIC</div>
            </div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════════
     SERVICES SECTION
══════════════════════════════════════════════════ -->
    <section class="pub-section" style="background:var(--bg-secondary)">
        <div class="pub-container">
            <div class="reveal">
                <div class="section-eyebrow">Our Services</div>
                <h2 class="section-title">Banking Solutions for Every Stage of Life</h2>
                <p class="section-subtitle">From your first savings account to a comprehensive retirement strategy,
                    Arcteron Trust has the products and expertise to help you succeed.</p>
            </div>
            <div class="services-grid">
                <div class="service-card reveal delay-1">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <rect x="2" y="5" width="20" height="14" rx="2" />
                            <line x1="2" y1="10" x2="22" y2="10" />
                        </svg>
                    </div>
                    <div class="service-card-title">Personal Banking</div>
                    <p class="service-card-desc">Checking and savings accounts designed around your life — with zero
                        monthly fees on select accounts, high-yield options, and a best-in-class mobile experience.</p>
                    <a href="/frontend/pages/personal-banking.html" class="service-card-link">Explore personal banking
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
                <div class="service-card reveal delay-2">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                        </svg>
                    </div>
                    <div class="service-card-title">Business Banking</div>
                    <p class="service-card-desc">Dedicated business checking, merchant payment processing, payroll
                        services, and credit solutions built to scale with your company's ambitions.</p>
                    <a href="/frontend/pages/business-banking.html" class="service-card-link">Explore business banking
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
                <div class="service-card reveal delay-3">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                    </div>
                    <div class="service-card-title">Wealth Management</div>
                    <p class="service-card-desc">Personalized investment advisory, estate planning, and trust services
                        crafted by Boston's most experienced private wealth advisors.</p>
                    <a href="/frontend/pages/wealth-management.html" class="service-card-link">Explore wealth management
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
                <div class="service-card reveal delay-1">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            <polyline points="9 22 9 12 15 12 15 22" />
                        </svg>
                    </div>
                    <div class="service-card-title">Home Loans</div>
                    <p class="service-card-desc">Competitive fixed and adjustable mortgage rates, FHA and jumbo loans,
                        with dedicated local underwriters who know the Boston real estate market.</p>
                    <a href="/frontend/pages/loans.html" class="service-card-link">Explore home loans <svg
                            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
                <div class="service-card reveal delay-2">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                        </svg>
                    </div>
                    <div class="service-card-title">Retirement Planning</div>
                    <p class="service-card-desc">IRAs, 401(k) rollovers, annuities, and pension advisory services — we
                        help you build a retirement income strategy you can depend on.</p>
                    <a href="/frontend/pages/wealth-management.html#retirement" class="service-card-link">Explore
                        retirement <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
                <div class="service-card reveal delay-3">
                    <div class="service-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                    </div>
                    <div class="service-card-title">Digital Security</div>
                    <p class="service-card-desc">Military-grade encryption, biometric authentication, real-time fraud
                        alerts, and 24/7 account monitoring keep your money and identity safe.</p>
                    <a href="/frontend/pages/personal-banking.html" class="service-card-link">Learn about security <svg
                            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     WHY ARCTERON — FEATURES
══════════════════════════════════════════════════ -->
    <section class="pub-section features-section">
        <div class="pub-container">
            <div style="text-align:center" class="reveal">
                <div class="section-eyebrow" style="justify-content:center">Why Arcteron Trust</div>
                <h2 class="section-title" style="text-align:center">Principles That Set Us Apart</h2>
                <p class="section-subtitle" style="margin:14px auto 0;text-align:center">Over two decades of serving
                    Boston's most discerning clients, built on an unwavering commitment to trust, innovation, and
                    personalized service.</p>
            </div>
            <div class="features-grid">
                <div class="feature-item reveal delay-1">
                    <div class="feature-icon-wrap">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                    </div>
                    <h3>Uncompromising Security</h3>
                    <p>Your funds are FDIC insured up to $250,000. Our technology platform employs 512-bit encryption,
                        multi-factor authentication, and AI-driven fraud detection running 24 hours a day.</p>
                </div>
                <div class="feature-item reveal delay-2">
                    <div class="feature-icon-wrap">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                    </div>
                    <h3>Cutting-Edge Innovation</h3>
                    <p>From instant account opening to real-time payment processing and AI-powered financial insights,
                        our digital platform puts powerful tools at your fingertips anywhere, anytime.</p>
                </div>
                <div class="feature-item reveal delay-3">
                    <div class="feature-icon-wrap">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                            <circle cx="9" cy="7" r="4" />
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                        </svg>
                    </div>
                    <h3>Personalized Service</h3>
                    <p>No call centers, no chatbots for important matters. Every Arcteron client is paired with a
                        dedicated relationship manager who understands your financial goals and life story.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     PRODUCTS HIGHLIGHT
══════════════════════════════════════════════════ -->
    <section class="pub-section" style="background:var(--bg-secondary)">
        <div class="pub-container">
            <div class="reveal">
                <div class="section-eyebrow">Our Products</div>
                <h2 class="section-title">Products Built for Your Life</h2>
            </div>
            <div class="products-row">
                <a href="/frontend/pages/personal-banking.html" class="product-card reveal delay-1">
                    <div class="product-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="2" y="5" width="20" height="14" rx="2" />
                            <line x1="2" y1="10" x2="22" y2="10" />
                        </svg>
                    </div>
                    <div class="product-card-name">Checking Account</div>
                    <p class="product-card-desc">Zero monthly fees. Free ATM access nationwide. Real-time alerts.</p>
                </a>
                <a href="/frontend/pages/personal-banking.html#savings" class="product-card reveal delay-2">
                    <div class="product-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <line x1="12" y1="1" x2="12" y2="23" />
                            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                        </svg>
                    </div>
                    <div class="product-card-name">High-Yield Savings</div>
                    <p class="product-card-desc">Earn up to 5.10% APY. FDIC insured. No minimums required.</p>
                </a>
                <a href="/frontend/pages/loans.html" class="product-card reveal delay-3">
                    <div class="product-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            <polyline points="9 22 9 12 15 12 15 22" />
                        </svg>
                    </div>
                    <div class="product-card-name">Mortgage Loans</div>
                    <p class="product-card-desc">Competitive rates from 6.25% APR. Local underwriters. Fast closing.</p>
                </a>
                <a href="/frontend/pages/wealth-management.html" class="product-card reveal delay-4">
                    <div class="product-card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                    </div>
                    <div class="product-card-name">Wealth Advisory</div>
                    <p class="product-card-desc">Bespoke portfolios. Risk-adjusted strategies. Expert advisors.</p>
                </a>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     ABOUT SPLIT
══════════════════════════════════════════════════ -->
    <section class="pub-section">
        <div class="pub-container">
            <div class="about-split">
                <div class="about-img-wrap reveal-left">
                    <img src="https://images.unsplash.com/photo-1486325212027-8081e485255e?w=900&q=80&auto=format&fit=crop"
                        alt="Arcteron Trust Boston office interior" loading="lazy">
                    <div class="about-badge">
                        <div class="about-badge-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                        </div>
                        <div class="about-badge-text">
                            <strong>Est. 2004</strong>
                            <span>Serving Boston for 20+ years</span>
                        </div>
                    </div>
                </div>
                <div class="reveal-right">
                    <div class="section-eyebrow">About Arcteron Trust</div>
                    <h2 class="section-title">A Boston Institution Built on Integrity</h2>
                    <p class="section-subtitle">Founded in Boston's Financial District in 2004, Arcteron Trust was built
                        with a single conviction: that banking should be personal, transparent, and built to last.</p>
                    <ul class="about-list">
                        <li>
                            <div class="about-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="3">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg></div>Headquartered at 100 Federal Street, Boston, MA 02110
                        </li>
                        <li>
                            <div class="about-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="3">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg></div>FDIC member institution — deposits insured up to $250,000
                        </li>
                        <li>
                            <div class="about-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="3">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg></div>Rated "Outstanding" by the Community Reinvestment Act
                        </li>
                        <li>
                            <div class="about-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="3">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg></div>Named Best Private Bank in New England — 2022, 2023, 2024
                        </li>
                        <li>
                            <div class="about-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="3">
                                    <polyline points="20 6 9 17 4 12" />
                                </svg></div>$2.8 billion in assets managed for 50,000+ clients
                        </li>
                    </ul>
                    <a href="/frontend/pages/about.html" class="about-link">Our full story <svg width="14" height="14"
                            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12" />
                            <polyline points="12 5 19 12 12 19" />
                        </svg></a>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     TESTIMONIALS
══════════════════════════════════════════════════ -->
    <section class="testimonials-section">
        <div class="pub-container">
            <div style="text-align:center" class="reveal">
                <div class="section-eyebrow" style="justify-content:center">Client Stories</div>
                <h2 class="section-title" style="text-align:center">Trusted by Thousands Across New England</h2>
            </div>
            <div class="testimonials-stage">
                <div class="testimonials-track" id="testimonialTrack"></div>
            </div>
            <div class="testimonials-nav">
                <button class="testimonial-arrow" id="testimonialPrev" aria-label="Previous testimonial">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="15 18 9 12 15 6" />
                    </svg>
                </button>
                <div class="testimonial-dots" id="testimonialDots"></div>
                <button class="testimonial-arrow" id="testimonialNext" aria-label="Next testimonial">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 18 15 12 9 6" />
                    </svg>
                </button>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     CTA BANNER
══════════════════════════════════════════════════ -->
    <section class="pub-section cta-section">
        <div class="pub-container">
            <div class="cta-inner reveal-scale">
                <div class="cta-eyebrow">Get Started Today</div>
                <h2 class="cta-title">Ready to Experience Banking<br>Done Differently?</h2>
                <p class="cta-subtitle">Join over 50,000 clients who trust Arcteron with their financial future. Open an
                    account in minutes — no branch visit required.</p>
                <div class="cta-actions">
                    <a href="/frontend/pages/register.html" class="cta-btn-white">Open an Account</a>
                    <a href="/frontend/pages/contact.html" class="cta-btn-outline">Talk to an Advisor</a>
                </div>
            </div>
        </div>
    </section>

    <!-- ═══════════════════════════════════════════════
     FOOTER
══════════════════════════════════════════════════ -->
    <footer class="pub-footer">
        <div class="pub-container">
            <div class="footer-grid">
                <!-- Brand -->
                <div>
                    <div class="footer-brand-logo">
                        <svg viewBox="0 0 40 40" fill="none">
                            <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
                            <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                            <path d="M14 23 H26" stroke="currentColor" stroke-width="1.5" opacity="0.6" />
                            <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.5" />
                        </svg>
                        <span class="footer-brand-name">Arcteron Trust</span>
                    </div>
                    <p class="footer-brand-desc">Private banking and wealth management services crafted for individuals,
                        families, and businesses in Boston and throughout New England.</p>
                    <address class="footer-address" style="font-style:normal">
                        100 Federal Street, Suite 2500<br>
                        Boston, MA 02110<br>
                        (617) 555-0200<br>
                        hello@arcterontrust.com
                    </address>
                    <div class="footer-fdic">
                        <div class="footer-fdic-dot"></div>
                        <span>FDIC Insured · Member FDIC</span>
                    </div>
                </div>
                <!-- Personal -->
                <div>
                    <div class="footer-col-title">Personal</div>
                    <ul class="footer-links">
                        <li><a href="/frontend/pages/personal-banking.html">Checking Accounts</a></li>
                        <li><a href="/frontend/pages/personal-banking.html#savings">Savings & CDs</a></li>
                        <li><a href="/frontend/pages/personal-banking.html#credit">Credit Cards</a></li>
                        <li><a href="/frontend/pages/loans.html">Home Loans</a></li>
                        <li><a href="/frontend/pages/loans.html#auto">Auto Loans</a></li>
                        <li><a href="/frontend/pages/loans.html#student">Student Loans</a></li>
                    </ul>
                </div>
                <!-- Business & Wealth -->
                <div>
                    <div class="footer-col-title">Business & Wealth</div>
                    <ul class="footer-links">
                        <li><a href="/frontend/pages/business-banking.html">Business Checking</a></li>
                        <li><a href="/frontend/pages/business-banking.html#merchant">Merchant Services</a></li>
                        <li><a href="/frontend/pages/business-banking.html#loans">Business Loans</a></li>
                        <li><a href="/frontend/pages/wealth-management.html">Investment Advisory</a></li>
                        <li><a href="/frontend/pages/wealth-management.html#retirement">Retirement Plans</a></li>
                        <li><a href="/frontend/pages/wealth-management.html#trust">Trust Services</a></li>
                    </ul>
                </div>
                <!-- Company & Legal -->
                <div>
                    <div class="footer-col-title">Company</div>
                    <ul class="footer-links">
                        <li><a href="/frontend/pages/about.html">About Us</a></li>
                        <li><a href="/frontend/pages/about.html#leadership">Leadership</a></li>
                        <li><a href="/frontend/pages/about.html#careers">Careers</a></li>
                        <li><a href="/frontend/pages/contact.html">Contact</a></li>
                        <li><a href="/frontend/pages/terms.html">Terms of Service</a></li>
                        <li><a href="/frontend/pages/privacy.html">Privacy Policy</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <p class="footer-copy">© <span class="current-year">2025</span> Arcteron Trust. All rights reserved. Deposits insured by the FDIC up to
                    $250,000 per depositor.</p>
                <div class="footer-legal-links">
                    <a href="/frontend/pages/terms.html">Terms</a>
                    <a href="/frontend/pages/privacy.html">Privacy</a>
                    <a href="/frontend/pages/contact.html">Contact</a>
                </div>
            </div>
        </div>
    </footer>

    <!-- Back to Top -->
    <button class="back-to-top" id="backToTop" aria-label="Back to top">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="18 15 12 9 6 15" />
        </svg>
    </button>

    <script src="/frontend/assets/js/public.js"></script>
</body>

</html>
```

---

### FRONTEND 13: auth.js
File Path: `frontend/assets/js/auth.js`

```js
const Auth = {
  PIN_SESSION_KEY: 'arcteronPinVerified',

  isLoggedIn() {
    return !!Api.getToken();
  },

  isPinSessionVerified() {
    return sessionStorage.getItem(this.PIN_SESSION_KEY) === '1';
  },

  markPinSessionVerified() {
    sessionStorage.setItem(this.PIN_SESSION_KEY, '1');
  },

  clearPinSession() {
    sessionStorage.removeItem(this.PIN_SESSION_KEY);
  },

  /**
   * Full gate: token, optional /me refresh for has_pin, set-pin vs enter-pin vs proceed.
   * Returns true only when the user may stay on the current protected page (e.g. dashboard).
   */
  async requireAuthAsync() {
    if (!this.isLoggedIn()) {
      Utils.navigateTo('/frontend/pages/login.html');
      return false;
    }

    let user = Api.getUser();
    if (!user) {
      Api.removeToken();
      Utils.navigateTo('/frontend/pages/login.html');
      return false;
    }

    if (typeof user.has_pin !== 'boolean') {
      const res = await Api.get('/api/auth/me', true);
      if (!res || !res.ok) {
        this.logout();
        return false;
      }
      Api.setUser(res.data);
      user = res.data;
    }

    const path = window.location.pathname || '';
    const onSetPin = path.includes('set-pin.html');
    const onEnterPin = path.includes('enter-pin.html');

    if (user.has_pin === false) {
      if (!onSetPin) {
        window.location.href = '/frontend/pages/set-pin.html';
        return false;
      }
      return true;
    }

    if (!this.isPinSessionVerified()) {
      if (!onEnterPin) {
        window.location.href = '/frontend/pages/enter-pin.html';
        return false;
      }
      return true;
    }

    return true;
  },

  requireGuest() {
    if (!this.isLoggedIn()) return;
    const user = Api.getUser();
    if (!user) {
      Api.removeToken();
      return;
    }
    if (typeof user.has_pin !== 'boolean' || user.has_pin === false) {
      Utils.navigateTo('/frontend/pages/set-pin.html');
      return;
    }
    if (!this.isPinSessionVerified()) {
      Utils.navigateTo('/frontend/pages/enter-pin.html');
      return;
    }
    this.redirectByRole(user);
  },

  redirectByRole(user) {
    if (user.role === 'superadmin') {
      Utils.navigateTo('/frontend/pages/superadmin/dashboard.html');
    } else if (user.role === 'admin') {
      Utils.navigateTo('/frontend/pages/admin/dashboard.html');
    } else {
      Utils.navigateTo('/frontend/pages/user/dashboard.html');
    }
  },

  logout() {
    this.clearPinSession();
    Api.removeToken();
    Utils.navigateTo('/frontend/pages/login.html');
  },

  getInitials(firstName, lastName) {
    return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
  }
};
```

---

### FRONTEND 14: vercel.json
File Path: `frontend/vercel.json`

```json
{
    "rewrites": [
        {
            "source": "/frontend/(.*)",
            "destination": "/$1"
        }
    ]
}
```

---

