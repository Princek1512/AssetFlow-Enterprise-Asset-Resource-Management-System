import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BookingStatusEnum
from app.schemas.common import AssetBrief, UserBrief


class BookingCreate(BaseModel):
    resource_id: uuid.UUID
    start_time: datetime
    end_time: datetime | None = None

    # Admin / Asset Manager only — lets them book a shared resource on someone else's
    # behalf. Any other role booking for themselves should simply omit this field.
    employee_id: uuid.UUID | None = None
    is_permanent: bool = False

    @model_validator(mode="after")
    def _check_time_window(self) -> "BookingCreate":
        if self.is_permanent and not self.end_time:
            self.end_time = datetime(2099, 12, 31, 23, 59, 59, tzinfo=self.start_time.tzinfo)
        if not self.end_time:
            raise ValueError("end_time is required if not a permanent allocation.")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID
    resource: AssetBrief | None = None
    employee_id: uuid.UUID
    employee: UserBrief | None = None
    start_time: datetime
    end_time: datetime
    status: BookingStatusEnum
    created_at: datetime


class BookingListOut(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[BookingOut]
