import uuid
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class AuditStatusEnum(str, enum.Enum):
    VERIFIED = "verified"
    MISSING = "missing"
    DAMAGED = "damaged"

audit_status_pg_enum = SAEnum(
    AuditStatusEnum,
    name="audit_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)

class AuditCycle(Base):
    __tablename__ = "audit_cycles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)

    records: Mapped[list["AuditRecord"]] = relationship(
        "AuditRecord", back_populates="cycle", cascade="all, delete-orphan"
    )

class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("audit_cycles.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    auditor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AuditStatusEnum] = mapped_column(
        audit_status_pg_enum, nullable=False, default=AuditStatusEnum.VERIFIED
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cycle: Mapped["AuditCycle"] = relationship("AuditCycle", back_populates="records")
    asset: Mapped["object"] = relationship("Asset")
    auditor: Mapped["object | None"] = relationship("User")
