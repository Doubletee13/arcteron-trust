from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from app.models.user import UserRole, UserStatus, IDType, CitizenshipStatus, EmploymentStatus, AccountPurpose


# --- Registration Schemas ---

class RegisterStep1(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: EmailStr
    phone: str
    password: str
    confirm_password: str

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
        return self


class RegisterStep2(BaseModel):
    date_of_birth: date
    citizenship_status: CitizenshipStatus
    ssn: Optional[str] = None
    itin: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    country: str = "United States"

    @field_validator("ssn")
    @classmethod
    def validate_ssn(cls, v):
        if v is not None:
            cleaned = v.replace("-", "")
            if len(cleaned) != 9 or not cleaned.isdigit():
                raise ValueError("SSN must be 9 digits")
        return v


class RegisterStep3(BaseModel):
    id_type: IDType
    id_number: str
    id_expiry_date: date
    employment_status: EmploymentStatus
    employer_name: Optional[str] = None
    annual_income: str
    source_of_income: str
    account_purpose: AccountPurpose


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
    created_at: datetime
    last_login: Optional[datetime] = None
    account: Optional[AccountResponse] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse