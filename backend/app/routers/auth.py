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
    RegisterStep4,
    OTPVerifyRequest,
    KYCSubmitRequest,
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
    generate_otp,
    verify_otp,
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


@router.post("/register/step3/{user_id}")
def register_step_three(user_id: str, data: RegisterStep3, db: Session = Depends(get_db)):
    user = register_step3(user_id, data, db)
    return {
        "message": "Step 3 complete. Proceed to step 4.",
        "user_id": str(user.id)
    }


@router.post("/register/step4/{user_id}")
def register_step_four(user_id: str, data: RegisterStep4, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.services.auth_service import register_step4
    result = register_step4(user_id, data, db)
    
    # Generate 6-digit OTP code and trigger email dispatch
    user = result["user"]
    user_email = user.email
    user_first_name = user.first_name
    
    otp_code = generate_otp(user_email)
    
    background_tasks.add_task(
        send_verification_email,
        user_email,
        user_first_name,
        otp_code
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
def request_email_verification(data: EmailVerificationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user and not user.is_email_verified:
        otp_code = generate_otp(user.email)
        background_tasks.add_task(
            send_verification_email,
            user.email,
            user.first_name,
            otp_code
        )
    # Always return success to avoid email enumeration
    return {"message": "If that email exists and is not verified, a verification code has been sent."}


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


@router.post("/email-verification/otp")
def confirm_email_otp(
    data: OTPVerifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    from app.services.email_service import send_welcome_email
    email = data.email.lower()
    
    if not verify_otp(email, data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_email_verified:
        return {"message": "Email already verified"}

    user.is_email_verified = True
    db.commit()
    db.refresh(user)

    # Create notification
    NotificationService.create_notification(
        db,
        user.id,
        "Email Verified",
        "Your email has been successfully verified. Please complete your identity verification (KYC).",
        NotificationType.email
    )
    db.commit()

    # Trigger welcome email in the background with account number
    if user.account:
        background_tasks.add_task(
            send_welcome_email,
            to=user.email,
            first_name=user.first_name,
            full_name=f"{user.first_name} {user.last_name}",
            account_number=user.account.account_number,
            account_type=user.account.account_type,
            country=user.country or "United States"
        )

    return {"message": "Email verified successfully"}


def upload_kyc_document(data_uri: str, user_id: str, doc_type: str) -> str:
    """Helper to decode base64 URI and upload to Supabase avatars bucket."""
    if not data_uri:
        return None
    if not data_uri.startswith('data:'):
        return data_uri

    try:
        header, encoded = data_uri.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        ext = "jpg" if "jpeg" in mime_type else mime_type.split("/")[1]
        file_bytes = base64.b64decode(encoded)
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            filename = f"kyc_{user_id}_{doc_type}.{ext}"
            upload_url = f"{supabase_url}/storage/v1/object/avatars/{filename}"
            headers = {
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": mime_type,
                "x-upsert": "true"
            }
            try:
                with httpx.Client(timeout=15.0) as client:
                    res = client.post(upload_url, headers=headers, content=file_bytes)
                    if res.status_code in (200, 201):
                        return f"{supabase_url}/storage/v1/object/public/avatars/{filename}"
                    else:
                        print(f"Supabase upload failed ({res.status_code}): {res.text[:200]}")
            except Exception as upload_err:
                print(f"Supabase upload exception: {upload_err}")
        
        return "https://ui-avatars.com/api/?name=KYC+Document"
    except Exception:
        return "https://ui-avatars.com/api/?name=KYC+Document"


@router.post("/kyc/submit")
def submit_kyc(
    data: KYCSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.status == UserStatus.blocked:
        raise HTTPException(status_code=403, detail="Account blocked. Please contact support.")

    # Upload files using base64 image data
    id_front_url = upload_kyc_document(data.id_front_data, str(current_user.id), "front")
    id_back_url = upload_kyc_document(data.id_back_data, str(current_user.id), "back")
    passport_photo_url = upload_kyc_document(data.passport_photo_data, str(current_user.id), "passport")

    current_user.title = data.title
    current_user.gender = data.gender
    current_user.date_of_birth = data.date_of_birth
    current_user.zip_code = data.zip_code
    current_user.ssn_encrypted = hash_password(data.ssn) if data.ssn else None
    if data.ssn:
        current_user.ssn_last_four = data.ssn.replace("-", "")[-4:]

    current_user.employment_status = data.employment_status
    current_user.employer_name = data.employer_name
    current_user.annual_income = data.annual_income
    current_user.source_of_income = data.source_of_income
    current_user.account_purpose = data.account_purpose

    current_user.address = data.address
    current_user.city = data.city
    current_user.state = data.state
    current_user.country = data.nationality

    current_user.next_of_kin_name = data.next_of_kin_name
    current_user.next_of_kin_address = data.next_of_kin_address
    current_user.next_of_kin_relationship = data.next_of_kin_relationship
    current_user.next_of_kin_age = data.next_of_kin_age

    current_user.id_type = data.id_type
    current_user.id_number = data.id_number
    current_user.id_expiry_date = data.id_expiry_date

    if id_front_url:
        current_user.id_front_image = id_front_url
    if id_back_url:
        current_user.id_back_image = id_back_url
    if passport_photo_url:
        current_user.profile_photo = passport_photo_url

    current_user.kyc_submitted_at = datetime.utcnow()
    current_user.is_kyc_complete = True
    current_user.status = UserStatus.pending

    db.commit()
    db.refresh(current_user)

    return {"message": "KYC submitted successfully. Account pending activation.", "user": user_to_response(current_user)}


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
            detail="Account blocked. Contact support@arcterontrust.com"
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
            detail="Account blocked. Contact support@arcterontrust.com"
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
                    raise HTTPException(status_code=500, detail=f"Storage upload failed: status={res.status_code} body={res.text}")
            
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