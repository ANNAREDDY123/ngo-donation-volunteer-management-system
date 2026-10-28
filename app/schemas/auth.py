from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.DONOR

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")

        return value

    @field_validator("role")
    @classmethod
    def validate_public_role(cls, value: UserRole) -> UserRole:
        if value not in {UserRole.DONOR, UserRole.VOLUNTEER}:
            raise ValueError(
                "This role cannot be assigned during registration."
            )

        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str | None = None