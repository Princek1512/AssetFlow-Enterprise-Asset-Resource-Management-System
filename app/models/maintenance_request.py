import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import MaintenancePriorityEnum, MaintenanceStatusEnum

maintenance_priority_pg_enum = SAEnum(
    MaintenancePriorityEnum,
    name="maintenance_priority_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)
maintenance_status_pg_enum = SAEnum(
    MaintenanceStatusEnum,
    name="maintenance_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[MaintenancePriorityEnum] = mapped_column(
        maintenance_priority_pg_enum, nullable=False, default=MaintenancePriorityEnum.MEDIUM
    )
    status: Mapped[MaintenanceStatusEnum] = mapped_column(
        maintenance_status_pg_enum, nullable=False, default=MaintenanceStatusEnum.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asset: Mapped["object"] = relationship("Asset")
    reported_by: Mapped["object | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<MaintenanceRequest asset={self.asset_id} status={self.status}>"
