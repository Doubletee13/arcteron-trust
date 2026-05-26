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
    sender_name = Column(String(200), nullable=True)
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