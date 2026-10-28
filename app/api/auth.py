
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, hash_password
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    issue_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Swagger uses this endpoint to obtain a bearer access token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Development-only temporary storage.
# Replace with persistent storage before production deployment.
_reset_tokens: dict[str, tuple[int, datetime]] = {}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token, "access")
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError, JWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive.",
        )

    return user


def require_roles(*allowed_roles: UserRole):
    def dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return current_user

    return dependency


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        return register_user(data, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


# JSON login endpoint for regular API clients.
@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        email=str(data.email),
        password=data.password,
        db=db,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password, or inactive account.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return issue_tokens(user)


# Form-based login endpoint for Swagger OAuth2 authorization.
@router.post("/token", response_model=TokenResponse)
def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password, or inactive account.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        payload = decode_token(data.refresh_token, "refresh")
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError, JWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    # Initial implementation; persistent refresh-token revocation
    # and rotation must be added before production deployment.
    return issue_tokens(user)


@router.get("/me", response_model=UserResponse)
def current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
)
def request_password_reset(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    email = str(data.email).strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    response = {
        "message": (
            "If the account exists, password-reset instructions "
            "will be provided."
        )
    }

    if user is not None and user.is_active:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_expire_minutes
        )

        _reset_tokens[token_hash] = (user.id, expires_at)

        # Development only: expose the token for local testing.
        # Production should deliver it through a secure email provider.
        if os.getenv("ENVIRONMENT", "development") != "production":
            response["reset_token"] = raw_token

    return response


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
)
def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    record = _reset_tokens.pop(token_hash, None)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password-reset token.",
        )

    user_id, expires_at = record

    if datetime.now(timezone.utc) >= expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password-reset token.",
        )

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password-reset request.",
        )

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {
        "message": "Password has been reset successfully."
    }


@router.patch(
    "/users/{user_id}/activation",
    response_model=UserResponse,
)
def set_user_activation(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/admin-check",
    response_model=MessageResponse,
)
def admin_check(
    admin: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    return {"message": "Super Admin access verified."}
