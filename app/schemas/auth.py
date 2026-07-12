import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RoleEnum


class SignupRequest(BaseModel):
    """Public signup — always results in an Employee account. Role is never accepted here."""
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: RoleEnum
    department_id: uuid.UUID | None
    is_active: bool


class PromoteUserRequest(BaseModel):
    """Admin-only. Restricted to the two promotable roles — Admin itself is never
    grantable through this endpoint to avoid accidental/malicious privilege escalation."""
    role: RoleEnum

    def validate_promotable(self) -> None:
        if self.role not in (RoleEnum.ASSET_MANAGER, RoleEnum.DEPARTMENT_HEAD, RoleEnum.EMPLOYEE):
            raise ValueError("role must be one of: asset_manager, department_head, employee")
