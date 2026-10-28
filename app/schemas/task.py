
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import (
    MilestoneStatus,
    TaskPriority,
    TaskStatus,
)


class MilestoneCreate(BaseModel):
    project_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    due_date: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    due_date: datetime | None = None
    status: MilestoneStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class MilestoneResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    due_date: datetime | None
    status: MilestoneStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    project_id: int = Field(gt=0)
    milestone_id: int | None = Field(default=None, gt=0)
    assignment_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class TaskUpdate(BaseModel):
    milestone_id: int | None = Field(default=None, gt=0)
    assignment_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
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


class TaskResponse(BaseModel):
    id: int
    project_id: int
    milestone_id: int | None
    assignment_id: int | None
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
