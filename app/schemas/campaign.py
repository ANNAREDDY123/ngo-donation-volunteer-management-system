
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.campaign import CampaignStatus


class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    goal_amount: int = Field(gt=0, le=2_000_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    start_date: datetime
    end_date: datetime

    @field_validator("title", "description")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")
        return self


class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    goal_amount: int | None = Field(default=None, gt=0, le=2_000_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: CampaignStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("End date cannot be before start date.")
        return self


class CampaignResponse(BaseModel):
    id: int
    title: str
    description: str
    goal_amount: int
    currency: str
    start_date: datetime
    end_date: datetime
    status: CampaignStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
