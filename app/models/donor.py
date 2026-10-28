import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DonorType(str, enum.Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class DonorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Donor(Base):
    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    full_name: Mapped[str] = mapped_column(
        String(150), nullable=False, index=True
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    donor_type: Mapped[DonorType] = mapped_column(
        Enum(DonorType, native_enum=False),
        nullable=False,
        default=DonorType.INDIVIDUAL,
    )

    organization_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    status: Mapped[DonorStatus] = mapped_column(
        Enum(DonorStatus, native_enum=False),
        nullable=False,
        default=DonorStatus.ACTIVE,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
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