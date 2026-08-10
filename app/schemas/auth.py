"""
Pydantic schemas for authentication requests and responses.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    role: Optional[str] = "viewer"


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Only non-privileged roles are assignable on registration."""
        if v in {UserRole.VIEWER, UserRole.GUEST}:
            return v
        return UserRole.VIEWER


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    api_quota: int


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str
