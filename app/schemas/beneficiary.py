
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.beneficiary import BeneficiaryCategory, BeneficiaryStatus


class BeneficiaryCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    category: BeneficiaryCategory
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    household_size: int | None = Field(default=None, ge=1, le=100)
    support_needs: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be empty")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                return None
            digits = "".join(char for char in value if char.isdigit())
            if not 7 <= len(digits) <= 15:
                raise ValueError("Phone number must contain 7 to 15 digits")
        return value

    @field_validator("address", "support_needs", "notes")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class BeneficiaryUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    category: BeneficiaryCategory | None = None
    status: BeneficiaryStatus | None = None
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    household_size: int | None = Field(default=None, ge=1, le=100)
    support_needs: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Full name cannot be empty")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                return None
            digits = "".join(char for char in value if char.isdigit())
            if not 7 <= len(digits) <= 15:
                raise ValueError("Phone number must contain 7 to 15 digits")
        return value

    @field_validator("address", "support_needs", "notes")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class BeneficiaryResponse(BaseModel):
    id: int
    full_name: str
    category: BeneficiaryCategory
    status: BeneficiaryStatus
    phone: str | None
    email: EmailStr | None
    address: str | None
    household_size: int | None
    support_needs: str | None
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
	