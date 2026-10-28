
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.volunteer import VolunteerStatus


class VolunteerCreate(BaseModel):
    user_id: int = Field(gt=0)
    phone: str = Field(min_length=7, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    skills: str | None = Field(default=None, max_length=3000)
    availability: str | None = Field(default=None, max_length=200)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValueError("Phone number must contain 7 to 15 digits.")
        return value

    @field_validator("address", "skills", "availability")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class VolunteerUpdate(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    skills: str | None = Field(default=None, max_length=3000)
    availability: str | None = Field(default=None, max_length=200)
    status: VolunteerStatus | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValueError("Phone number must contain 7 to 15 digits.")
        return value

    @field_validator("address", "skills", "availability")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class VolunteerResponse(BaseModel):
    id: int
    user_id: int
    phone: str
    address: str | None
    skills: str | None
    availability: str | None
    status: VolunteerStatus

    model_config = ConfigDict(from_attributes=True)
