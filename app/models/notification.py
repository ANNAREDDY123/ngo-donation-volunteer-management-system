
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class NotificationType(str, Enum):
    GENERAL = "general"
    DONATION = "donation"
    VOLUNTEER = "volunteer"
    PROJECT = "project"
    MILESTONE = "milestone"
    IMPACT = "impact"
    SYSTEM = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, native_enum=False),
        default=NotificationType.GENERAL,
        nullable=False,
        index=True,
    )

    related_entity_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )
    related_entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
