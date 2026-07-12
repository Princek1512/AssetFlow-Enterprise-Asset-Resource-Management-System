import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MaintenancePriorityEnum, MaintenanceStatusEnum
from app.schemas.common import AssetBrief, UserBrief


class MaintenanceCreate(BaseModel):
    asset_id: uuid.UUID
    issue_description: str = Field(min_length=1, max_length=2000)
    priority: MaintenancePriorityEnum = MaintenancePriorityEnum.MEDIUM


class MaintenanceStatusUpdate(BaseModel):
    """
    Drives the Pending -> Approved -> In Progress -> Completed (or -> Rejected)
    workflow. `status` is the *target* state; the endpoint validates the transition
    against `maintenance_state_machine` and applies the matching Asset side effect
    (see app/services/maintenance_lifecycle.py) atomically in the same transaction.
    """
    status: MaintenanceStatusEnum


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    asset: AssetBrief | None = None
    reported_by_id: uuid.UUID | None = None
    reported_by: UserBrief | None = None
    issue_description: str
    priority: MaintenancePriorityEnum
    status: MaintenanceStatusEnum
    created_at: datetime
    resolved_at: datetime | None = None


class MaintenanceListOut(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[MaintenanceOut]
