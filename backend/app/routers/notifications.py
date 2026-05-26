from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationStatus
from typing import Optional
from datetime import datetime
from uuid import UUID

router = APIRouter(prefix="/api/notifications", tags=["Notifications"], redirect_slashes=False)


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status == NotificationStatus.unread
    ).count()
    return {"count": count}


@router.post("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.status == NotificationStatus.unread
    ).update({"status": NotificationStatus.read})
    db.commit()
    return {"success": True, "updated_count": updated}


@router.get("")
@router.get("/")
def get_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    # Build query
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    # Apply filters
    if type:
        try:
            notif_type = NotificationType(type)
            query = query.filter(Notification.type == notif_type)
        except ValueError:
            pass  # Invalid type, ignore filter

    if status:
        try:
            notif_status = NotificationStatus(status)
            query = query.filter(Notification.status == notif_status)
        except ValueError:
            pass  # Invalid status, ignore filter

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.filter(Notification.created_at >= from_dt)
        except ValueError:
            pass  # Invalid date, ignore filter

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.filter(Notification.created_at <= to_dt)
        except ValueError:
            pass  # Invalid date, ignore filter

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page).all()

    return {
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "type": n.type.value if n.type else "system",
                "status": n.status.value if n.status else "unread",
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "related_id": str(n.related_id) if n.related_id else None,
                "related_type": n.related_type,
                "data": n.data
            }
            for n in notifications
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.delete("/all")
def delete_all_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(Notification.user_id == current_user.id).delete()
    db.commit()

    return {"success": True}


@router.get("/{notification_id}")
def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        notif_id = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {
        "id": str(notif.id),
        "title": notif.title,
        "message": notif.message,
        "type": notif.type.value if notif.type else "system",
        "status": notif.status.value if notif.status else "unread",
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "related_id": str(notif.related_id) if notif.related_id else None,
        "related_type": notif.related_type,
        "data": notif.data
    }


@router.post("/{notification_id}/mark-read")
def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        notif_id = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.status = NotificationStatus.read
    db.commit()

    return {"success": True}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        notif_id = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()

    return {"success": True}