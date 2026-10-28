
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.expense import ExpenseCategory


class ExpenseCreate(BaseModel):
    project_id: int = Field(gt=0)
    category: ExpenseCategory
    amount: int = Field(gt=0, le=100_000_000)
    description: str = Field(min_length=1, max_length=500)
    expense_date: date = Field(default_factory=date.today)
    receipt_reference: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be empty")
        return value

    @field_validator("receipt_reference", "notes")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ExpenseUpdate(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    category: ExpenseCategory | None = None
    amount: int | None = Field(default=None, gt=0, le=100_000_000)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    expense_date: date | None = None
    receipt_reference: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Description cannot be empty")
        return value

    @field_validator("receipt_reference", "notes")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ExpenseResponse(BaseModel):
    id: int
    project_id: int
    category: ExpenseCategory
    amount: int
    description: str
    expense_date: date
    receipt_reference: str | None
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
