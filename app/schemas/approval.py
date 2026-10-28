
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project_approval import ApprovalStatus


class ApprovalSubmit(BaseModel):
    comments: str | None = Field(default=None, max_length=2000)

    @field_validator("comments")
    @classmethod
    def clean_comments(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ApprovalDecision(BaseModel):
    decision: ApprovalStatus
    comments: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value):
        if value not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise ValueError("Decision must be approved or rejected")
        return value

    @field_validator("comments")
    @classmethod
    def clean_comments(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class ApprovalResponse(BaseModel):
    id: int
    project_id: int
    submitted_by: int
    status: ApprovalStatus
    submission_comments: str | None
    reviewed_by: int | None
    review_comments: str | None
    submitted_at: datetime
    reviewed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
