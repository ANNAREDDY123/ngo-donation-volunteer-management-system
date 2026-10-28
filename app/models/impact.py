
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ImpactStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    NOT_ACHIEVED = "not_achieved"


class ProjectImpact(Base):
    __tablename__ = "project_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    beneficiary_id: Mapped[int | None] = mapped_column(
        ForeignKey("beneficiaries.id"),
        nullable=True,
        index=True,
    )

    metric_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[ImpactStatus] = mapped_column(
        SAEnum(ImpactStatus, native_enum=False),
        default=ImpactStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )

    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
