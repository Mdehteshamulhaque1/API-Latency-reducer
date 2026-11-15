"""Request and response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from esone_api.models import Role

USERNAME_MIN, USERNAME_MAX = 3, 100
PASSWORD_MIN, PASSWORD_MAX = 8, 100


class UserCreate(BaseModel):
    username: str = Field(..., min_length=USERNAME_MIN, max_length=USERNAME_MAX)
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)

    @field_validator("username")
    @classmethod
    def _clean_username(cls, value: str) -> str:
        value = value.strip()
        if not value.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username may contain letters, digits, '-', '_' and '.' only")
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
