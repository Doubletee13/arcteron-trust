import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
from app.database import Base


class CodeType(str, enum.Enum):
    cot = "cot"
    bop = "bop"


class COTCode(Base):
    __tablename__ = "cot_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User who owns the code
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Admin who generated the code
    generated_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Code details
    code_type = Column(SQLEnum(CodeType), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Usage tracking
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    generated_by_admin = relationship("User", foreign_keys=[generated_by_admin_id])
