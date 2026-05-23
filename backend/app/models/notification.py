import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import enum
from app.database import Base


class NotificationType(str, enum.Enum):
    transaction = "transaction"
    security = "security"
    system = "system"
    admin = "admin"
    email = "email"
    profile = "profile"
    password = "password"
    device = "device"
    warning = "warning"
    success = "success"


class NotificationStatus(str, enum.Enum):
    unread = "unread"
    read = "read"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    type = Column(Enum(NotificationType), default=NotificationType.system)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.unread)
    related_id = Column(UUID(as_uuid=True), nullable=True)
    related_type = Column(String(50), nullable=True)
    data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="notifications")