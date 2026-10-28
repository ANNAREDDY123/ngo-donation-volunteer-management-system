
from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    EDUCATION = "education"
    MEDICAL = "medical"
    EQUIPMENT = "equipment"
    STAFF = "staff"
    UTILITIES = "utilities"
    ACCOMMODATION = "accommodation"
    OTHER = "other"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    category: Mapped[ExpenseCategory] = mapped_column(
        SAEnum(ExpenseCategory, native_enum=False),
        nullable=False,
        index=True,
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=False)

    expense_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        index=True,
    )

    receipt_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

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
