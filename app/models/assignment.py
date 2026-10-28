
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    volunteer_id: Mapped[int] = mapped_column(
        ForeignKey("volunteers.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[AssignmentPriority] = mapped_column(
        Enum(AssignmentPriority, native_enum=False),
        default=AssignmentPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
