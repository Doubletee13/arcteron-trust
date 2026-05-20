from fastapi import APIRouter, Depends, HTTPException
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
)
from app.services.auth_service import (
    register_step1,
    register_step2,
    register_step3,
    login_user,
)
from app.middleware.auth import get_current_user
from app.models.user import User

from app.utils.tokens import (
    generate_reset_token,
    verify_reset_token,
    generate_pin_reset_token,
    verify_pin_reset_token,
)
from app.services.email_service import send_password_reset_email, send_pin_reset_email
from app.utils.hashing import hash_password, hash_pin, verify_pin

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
def register_step_three(user_id: str, data: RegisterStep3, db: Session = Depends(get_db)):
    result = register_step3(user_id, data, db)
    return result


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(data, db)
    return result


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
    if not current_user.transaction_pin:
        raise HTTPException(status_code=400, detail="No PIN set. Please set your PIN first.")
    if not verify_pin(pin, current_user.transaction_pin):
        raise HTTPException(status_code=401, detail="Incorrect PIN.")
    return {"message": "PIN verified", "verified": True}