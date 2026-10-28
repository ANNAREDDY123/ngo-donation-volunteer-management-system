
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=5000)
    notification_type: NotificationType = NotificationType.GENERAL
    related_entity_type: str | None = Field(default=None, max_length=80)
    related_entity_id: int | None = Field(default=None, gt=0)

    @field_validator("title", "message")
    @classmethod
    def validate_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("related_entity_type")
    @classmethod
    def clean_entity_type(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    related_entity_type: str | None
    related_entity_id: int | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int
