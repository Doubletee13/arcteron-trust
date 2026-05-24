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

    # Send verification email
    try:
        token = generate_verification_token(user.email)
        send_verification_email(user.email, user.first_name, token)
    except Exception:
        # Never block registration because email failed
        pass

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

    # Create bank account
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

    if user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked. Contact support."
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