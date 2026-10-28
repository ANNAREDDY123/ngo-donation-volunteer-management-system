
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.notifications import (
    create_notification_from_payload,
    delete_notification,
    get_notification_for_user,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

NOTIFICATION_MANAGERS = (
    UserRole.SUPER_ADMIN,
    UserRole.NGO_MANAGER,
    UserRole.VOLUNTEER_COORDINATOR,
)


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notification_endpoint(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*NOTIFICATION_MANAGERS)),
):
    try:
        return create_notification_from_payload(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=NotificationListResponse)
def list_notifications_endpoint(
    unread_only: bool = False,
    notification_type: NotificationType | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        skip=skip,
        limit=limit,
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_notification_for_user(
            db, notification_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return mark_notification_read(
            db, notification_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/read-all")
def mark_all_notifications_read_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = mark_all_notifications_read(db, current_user.id)
    return {"message": "Unread notifications marked as read", "updated_count": count}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_notification(db, notification_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
