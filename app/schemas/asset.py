import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssetConditionEnum, AssetStatusEnum


class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category_id: uuid.UUID
    serial_number: str | None = Field(default=None, max_length=150)
    condition: AssetConditionEnum = AssetConditionEnum.NEW
    location: str | None = Field(default=None, max_length=200)
    is_bookable: bool = False

    # Registration never accepts `status` or `asset_tag` directly — status always
    # starts at AVAILABLE and asset_tag is server-generated (see app/api/v1/assets.py).


class AssetUpdate(BaseModel):
    """
    Editable directory fields — PATCH semantics, only provided fields change.
    Deliberately excludes `status`: that's only mutable via the guarded
    /assets/{id}/status endpoint so every transition passes through the
    asset lifecycle state machine.
    """

    name: str | None = Field(default=None, min_length=2, max_length=200)
    category_id: uuid.UUID | None = None
    serial_number: str | None = Field(default=None, max_length=150)
    condition: AssetConditionEnum | None = None
    location: str | None = Field(default=None, max_length=200)
    is_bookable: bool | None = None


class AssetCategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_tag: str
    name: str
    category_id: uuid.UUID
    category: AssetCategoryBrief | None = None
    serial_number: str | None
    condition: AssetConditionEnum
    location: str | None
    status: AssetStatusEnum
    is_bookable: bool
    current_holder_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class AssetListOut(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[AssetOut]


class AssetStatusTransitionRequest(BaseModel):
    status: AssetStatusEnum
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional note on why the status is changing (audit/logging use in later phases).",
    )


class AssetAllocateRequest(BaseModel):
    """Direct allocation — only valid for non-bookable assets (see Asset.is_bookable)."""

    employee_id: uuid.UUID
    note: str | None = Field(default=None, max_length=500)
