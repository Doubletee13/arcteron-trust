import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
from app.database import Base


class CodeType(str, enum.Enum):
    COT = "COT"
    BOP = "BOP"
    IMF = "IMF"
    TAX = "TAX"


class TransactionCode(Base):
    __tablename__ = "transaction_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_type = Column(Enum(CodeType), nullable=False)
    code_value = Column(String(100), unique=True, nullable=False)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_to_transaction_id = Column(UUID(as_uuid=True), nullable=True)
    generated_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)