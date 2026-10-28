
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    location: str | None = Field(default=None, max_length=300)
    start_date: datetime
    end_date: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")
        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    location: str | None = Field(default=None, max_length=300)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: ProjectStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("End date cannot be before start date.")
        return self


class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str
    location: str | None
    start_date: datetime
    end_date: datetime | None
    status: ProjectStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
