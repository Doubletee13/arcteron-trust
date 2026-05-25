import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
from app.database import Base


class AdminTransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class AdminTransferType(str, enum.Enum):
    local = "local"
    international = "international"


class AdminTransaction(Base):
    __tablename__ = "admin_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Admin who performed the action
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # User whose account was affected
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(SQLEnum(AdminTransactionType), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    
    # Custom fields for admin transactions
    sender_name = Column(String(255), nullable=True)
    bank_name = Column(String(255), nullable=True)
    transfer_type = Column(SQLEnum(AdminTransferType), nullable=True)
    description = Column(Text, nullable=True)
    account_number = Column(String(20), nullable=True)
    
    # Custom transaction date (optional, defaults to created_at)
    transaction_date = Column(DateTime, nullable=True)
    
    # Reference
    reference = Column(String(50), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = relationship("User", foreign_keys=[admin_id])
    user = relationship("User", foreign_keys=[user_id])
