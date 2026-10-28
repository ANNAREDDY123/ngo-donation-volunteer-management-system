
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.impact import ImpactStatus


class ImpactCreate(BaseModel):
    project_id: int = Field(gt=0)
    beneficiary_id: int | None = Field(default=None, gt=0)
    metric_name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    unit: str = Field(min_length=1, max_length=50)
    target_value: int = Field(gt=0, le=1_000_000_000)
    actual_value: int = Field(default=0, ge=0, le=1_000_000_000)

    @field_validator("metric_name", "unit")
    @classmethod
    def clean_required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ImpactUpdate(BaseModel):
    beneficiary_id: int | None = Field(default=None, gt=0)
    metric_name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    target_value: int | None = Field(default=None, gt=0, le=1_000_000_000)
    actual_value: int | None = Field(default=None, ge=0, le=1_000_000_000)

    @field_validator("metric_name", "unit")
    @classmethod
    def clean_required_text(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ImpactResponse(BaseModel):
    id: int
    project_id: int
    beneficiary_id: int | None
    metric_name: str
    description: str | None
    unit: str
    target_value: int
    actual_value: int
    progress_percentage: float
    status: ImpactStatus
    recorded_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
