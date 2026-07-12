import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransferRequestStatusEnum
from app.schemas.common import AssetBrief, UserBrief


class TransferRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class TransferRequestDecision(BaseModel):
    """Used by both approve and reject — reason is optional context for the decision."""

    reason: str | None = Field(default=None, max_length=500)


class TransferRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    asset: AssetBrief | None = None
    requested_by_id: uuid.UUID
    requested_by: UserBrief | None = None
    current_holder_id: uuid.UUID | None
    current_holder: UserBrief | None = None
    reason: str | None
    status: TransferRequestStatusEnum
    created_at: datetime
    resolved_at: datetime | None
