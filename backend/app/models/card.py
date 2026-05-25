import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    
    card_number = Column(String(20), unique=True, nullable=False, index=True)
    card_holder_name = Column(String(100), nullable=False)
    expiry_date = Column(String(5), nullable=False)
    cvv = Column(String(4), nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_physical = Column(Boolean, default=True)
    card_type = Column(String(20), default="debit")
    network = Column(String(20), default="mastercard")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    account = relationship("Account")
