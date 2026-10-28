from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.donor import DonorStatus, DonorType


class DonorCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    donor_type: DonorType = DonorType.INDIVIDUAL
    organization_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValueError("Phone number must contain 7 to 15 digits.")
        return value

    @model_validator(mode="after")
    def validate_organization(self):
        if self.donor_type == DonorType.ORGANIZATION:
            if not self.organization_name or not self.organization_name.strip():
                raise ValueError(
                    "Organization name is required for organization donors."
                )
        return self


class DonorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    donor_type: DonorType | None = None
    organization_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    status: DonorStatus | None = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 7 <= len(digits) <= 15:
            raise ValueError("Phone number must contain 7 to 15 digits.")
        return value


class DonorResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str
    donor_type: DonorType
    organization_name: str | None
    address: str | None
    status: DonorStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)