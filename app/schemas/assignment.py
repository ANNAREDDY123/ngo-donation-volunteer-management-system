
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.assignment import AssignmentPriority, AssignmentStatus


class AssignmentCreate(BaseModel):
    volunteer_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: AssignmentPriority = AssignmentPriority.MEDIUM
    due_date: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    priority: AssignmentPriority | None = None
    status: AssignmentStatus | None = None
    due_date: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class AssignmentResponse(BaseModel):
    id: int
    volunteer_id: int
    title: str
    description: str
    priority: AssignmentPriority
    status: AssignmentStatus
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
