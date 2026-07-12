import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, Sequence, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import AssetConditionEnum, AssetStatusEnum

# Standalone Postgres sequence backing human-readable asset tags (AF-0001, AF-0002, ...).
# Registered on Base.metadata so `Base.metadata.create_all` provisions it alongside the
# tables. The app pulls the next value explicitly (see app/api/v1/assets.py) rather than
# wiring it as a column server_default, so the formatted tag string can be computed and
# assigned in the same INSERT instead of needing a round-trip after insert.
asset_tag_sequence = Sequence("asset_tag_seq", start=1, metadata=Base.metadata)

asset_condition_pg_enum = SAEnum(
    AssetConditionEnum,
    name="asset_condition_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)
asset_status_pg_enum = SAEnum(
    AssetStatusEnum,
    name="asset_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("asset_categories.id", ondelete="RESTRICT"), nullable=False
    )

    # Auto-generated sequential human-readable tag, e.g. AF-0001.
    # `tag_sequence` is the raw integer pulled from `asset_tag_sequence` (above) that
    # `asset_tag` is formatted from; kept here so the format logic has a stable integer
    # to key off instead of parsing strings back out of asset_tag.
    tag_sequence: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    asset_tag: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    serial_number: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True)
    condition: Mapped[AssetConditionEnum] = mapped_column(
        asset_condition_pg_enum, nullable=False, default=AssetConditionEnum.NEW
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[AssetStatusEnum] = mapped_column(
        asset_status_pg_enum, nullable=False, default=AssetStatusEnum.AVAILABLE
    )

    # Shared/bookable resources (rooms, vehicles, shared equipment) go through the
    # Booking workflow (Phase 3); non-bookable assets go through direct Allocation.
    is_bookable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Current holder for directly-allocated (non-bookable) assets.
    # This is the field the Phase 3 double-allocation lock guards.
    current_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category: Mapped["AssetCategory"] = relationship("AssetCategory")
    current_holder: Mapped["object | None"] = relationship("User", foreign_keys=[current_holder_id])

    def __repr__(self) -> str:
        return f"<Asset {self.asset_tag} - {self.name} status={self.status}>"
