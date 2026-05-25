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
    pending = "pending"


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