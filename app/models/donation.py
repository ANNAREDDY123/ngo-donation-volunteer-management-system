
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DonationStatus(str, enum.Enum):
    PLEDGED = "pledged"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    CARD = "card"
    CHEQUE = "cheque"
    OTHER = "other"


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    donor_id: Mapped[int] = mapped_column(
        ForeignKey("donors.id"), nullable=False, index=True
    )

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False, index=True
    )

    amount: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR"
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False),
        nullable=False,
    )

    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, native_enum=False),
        nullable=False,
        default=DonationStatus.PENDING,
        index=True,
    )

    transaction_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    donation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
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
