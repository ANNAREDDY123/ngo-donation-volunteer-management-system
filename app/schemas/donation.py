
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.donation import DonationStatus, PaymentMethod


class DonationCreate(BaseModel):
    donor_id: int = Field(gt=0)
    campaign_id: int = Field(gt=0)
    amount: int = Field(gt=0, le=2_000_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    payment_method: PaymentMethod
    transaction_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return value

    @field_validator("transaction_reference")
    @classmethod
    def normalize_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Transaction reference cannot be empty.")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DonationUpdate(BaseModel):
    status: DonationStatus | None = None
    transaction_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("transaction_reference")
    @classmethod
    def normalize_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Transaction reference cannot be empty.")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DonationResponse(BaseModel):
    id: int
    donor_id: int
    campaign_id: int
    amount: int
    currency: str
    payment_method: PaymentMethod
    status: DonationStatus
    transaction_reference: str | None
    notes: str | None
    donation_date: datetime
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
