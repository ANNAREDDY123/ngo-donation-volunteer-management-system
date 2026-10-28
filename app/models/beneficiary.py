
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class BeneficiaryCategory(str, Enum):
    CHILDREN = "children"
    WOMEN = "women"
    ELDERLY = "elderly"
    PERSONS_WITH_DISABILITIES = "persons_with_disabilities"
    LOW_INCOME_FAMILIES = "low_income_families"
    HOMELESS = "homeless"
    OTHER = "other"


class BeneficiaryStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    category: Mapped[BeneficiaryCategory] = mapped_column(
        SAEnum(BeneficiaryCategory, native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[BeneficiaryStatus] = mapped_column(
        SAEnum(BeneficiaryStatus, native_enum=False),
        default=BeneficiaryStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    household_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_needs: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(
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
