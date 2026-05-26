import uuid
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    routing_number = Column(String(20), nullable=True, default="011400754")
    account_type = Column(String(50), default="checking")
    balance = Column(Numeric(precision=18, scale=2), default=0.00)
    currency = Column(String(10), default="USD")
    is_frozen = Column(Boolean, default=False)
    swift_code = Column(String(20), nullable=True, default="ARCTUSD1")
    bank_name = Column(String(100), default="Arcteron Trust")
    
    # --- Blocking Info ---
    blocked_at = Column(DateTime, nullable=True)
    blocked_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="account")