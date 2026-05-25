from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType
from app.models.user import User
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: UUID,
        title: str,
        message: str,
        notif_type: NotificationType,
        related_id: Optional[UUID] = None,
        related_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None
    ) -> Notification:
        """
        Create a notification for a user
        
        Args:
            db: Database session
            user_id: User ID to notify
            title: Notification title
            message: Notification message
            notif_type: Type of notification
            related_id: Optional related entity ID
            related_type: Optional related entity type
            data: Optional additional data
            
        Returns:
            Created notification object
        """
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            related_id=related_id,
            related_type=related_type,
            data=data
        )
        if created_at is not None:
            notif.created_at = created_at
        db.add(notif)
        return notif
    
    @staticmethod
    def create_transfer_notification(
        db: Session,
        sender_id: UUID,
        recipient_id: UUID,
        amount: float,
        sender_name: str,
        recipient_name: str,
        reference: str,
        transaction_id: UUID
    ):
        """
        Create notifications for both sender and recipient of a transfer
        
        Args:
            db: Database session
            sender_id: Sender user ID
            recipient_id: Recipient user ID
            amount: Transfer amount
            sender_name: Sender's full name
            recipient_name: Recipient's full name
            reference: Transaction reference
            transaction_id: Transaction ID
        """
        # Notification for sender
        NotificationService.create_notification(
            db, sender_id,
            "Transfer Sent",
            f"You sent ${amount:,.2f} to {recipient_name}. Ref: {reference}",
            NotificationType.transaction,
            related_id=transaction_id,
            related_type="transaction",
            data={
                "amount": amount,
                "recipient": recipient_name,
                "reference": reference
            }
        )
        
        # Notification for recipient
        NotificationService.create_notification(
            db, recipient_id,
            "Money Received",
            f"You received ${amount:,.2f} from {sender_name}. Ref: {reference}",
            NotificationType.transaction,
            related_id=transaction_id,
            related_type="transaction",
            data={
                "amount": amount,
                "sender": sender_name,
                "reference": reference
            }
        )
    
    @staticmethod
    def create_security_notification(
        db: Session,
        user_id: UUID,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Create a security notification
        
        Args:
            db: Database session
            user_id: User ID to notify
            title: Notification title
            message: Notification message
            data: Optional additional data
        """
        NotificationService.create_notification(
            db, user_id,
            title,
            message,
            NotificationType.security,
            data=data
        )
    
    @staticmethod
    def create_system_notification(
        db: Session,
        user_id: UUID,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Create a system notification
        
        Args:
            db: Database session
            user_id: User ID to notify
            title: Notification title
            message: Notification message
            data: Optional additional data
        """
        NotificationService.create_notification(
            db, user_id,
            title,
            message,
            NotificationType.system,
            data=data
        )
