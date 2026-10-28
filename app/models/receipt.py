
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DonationReceipt(Base):
    __tablename__ = "donation_receipts"

    __table_args__ = (
        UniqueConstraint("donation_id", name="uq_receipt_donation"),
        UniqueConstraint("receipt_number", name="uq_receipt_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    receipt_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    donation_id: Mapped[int] = mapped_column(
        ForeignKey("donations.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    issued_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
