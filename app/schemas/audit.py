import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.audit import AuditStatusEnum
from app.schemas.common import AssetBrief, UserBrief

class AuditRecordCreate(BaseModel):
    asset_id: uuid.UUID
    status: AuditStatusEnum
    notes: str | None = None

class AuditRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cycle_id: uuid.UUID
    asset_id: uuid.UUID
    asset: AssetBrief | None = None
    auditor_id: uuid.UUID | None = None
    auditor: UserBrief | None = None
    status: AuditStatusEnum
    notes: str | None = None
    timestamp: datetime

class AuditCycleCreate(BaseModel):
    name: str
    description: str | None = None

class AuditCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    created_at: datetime
    is_completed: bool

class DiscrepancyReport(BaseModel):
    missing: list[AuditRecordOut]
    damaged: list[AuditRecordOut]
    unaudited_assets: list[AssetBrief]
