from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from app.models.user import (
    User,
    UserRole,
    UserStatus,
    IDType,
    CitizenshipStatus,
    EmploymentStatus,
    AccountPurpose,
)


# --- Registration Schemas ---

class RegisterStep1(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    username: str

class RegisterStep2(BaseModel):
    email: EmailStr
    phone: str
    country: str

class RegisterStep3(BaseModel):
    currency: str
    account_type: str
    pin: str
    confirm_pin: Optional[str] = None

    @field_validator("pin")
    @classmethod
    def pin_length(cls, v):
        if len(v) != 4 or not v.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        return v

class RegisterStep4(BaseModel):
    password: str
    confirm_password: str
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("You must accept the Terms of Service and Privacy Policy")
        return self


# --- OTP & KYC Schemas ---

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class KYCSubmitRequest(BaseModel):
    title: str
    gender: str
    date_of_birth: date
    zip_code: str
    ssn: Optional[str] = None
    employment_status: EmploymentStatus
    employer_name: Optional[str] = None
    annual_income: str
    source_of_income: str
    account_purpose: AccountPurpose
    address: str
    city: str
    state: str
    nationality: str
    next_of_kin_name: str
    next_of_kin_address: str
    next_of_kin_relationship: str
    next_of_kin_age: int
    id_type: IDType
    id_number: str
    id_expiry_date: date
    id_front_data: Optional[str] = None  # Base64 raw image
    id_back_data: Optional[str] = None   # Base64 raw image
    passport_photo_data: Optional[str] = None  # Base64 raw image


# --- Login Schema ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- Password & PIN Schemas ---

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class SetPinRequest(BaseModel):
    pin: str
    confirm_pin: str

    @field_validator("pin")
    @classmethod
    def pin_length(cls, v):
        if len(v) != 4 or not v.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @model_validator(mode="after")
    def pins_match(self):
        if self.pin != self.confirm_pin:
            raise ValueError("PINs do not match")
        return self


class PinResetRequest(BaseModel):
    email: EmailStr


class PinResetConfirm(BaseModel):
    token: str
    new_pin: str
    confirm_pin: str

    @model_validator(mode="after")
    def pins_match(self):
        if self.new_pin != self.confirm_pin:
            raise ValueError("PINs do not match")
        return self


# --- Email Verification Schemas ---

class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    token: str


# --- Profile Update Schemas ---

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class PhotoUploadRequest(BaseModel):
    photo_data: str  # Base64 encoded image


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str
    confirm_pin: str

    @field_validator("new_pin")
    @classmethod
    def pin_format(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @model_validator(mode="after")
    def pins_match(self):
        if self.new_pin != self.confirm_pin:
            raise ValueError("PINs do not match")
        return self


# --- Response Schemas ---

class AccountResponse(BaseModel):
    account_number: str
    routing_number: str
    account_type: str
    balance: float
    currency: str
    swift_code: str
    bank_name: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    username: Optional[str] = None
    email: str
    phone: Optional[str] = None
    role: UserRole
    status: UserStatus
    is_email_verified: bool
    is_kyc_complete: bool
    is_id_verified: bool
    date_of_birth: Optional[date] = None
    citizenship_status: Optional[CitizenshipStatus] = None
    ssn_last_four: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    id_type: Optional[IDType] = None
    employment_status: Optional[EmploymentStatus] = None
    annual_income: Optional[str] = None
    account_purpose: Optional[AccountPurpose] = None
    profile_photo: Optional[str] = None
    title: Optional[str] = None
    gender: Optional[str] = None
    has_accepted_terms: bool = False
    kyc_submitted_at: Optional[datetime] = None
    next_of_kin_name: Optional[str] = None
    next_of_kin_address: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_age: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    account: Optional[AccountResponse] = None
    has_pin: bool = False

    model_config = {"from_attributes": True}


def user_to_response(user: User) -> UserResponse:
    """Serialize user for API; has_pin reflects stored transaction PIN (hash never exposed)."""
    return UserResponse.model_validate(user).model_copy(
        update={"has_pin": bool(user.transaction_pin)}
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse