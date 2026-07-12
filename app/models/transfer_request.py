import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import TransferRequestStatusEnum

transfer_status_pg_enum = SAEnum(
    TransferRequestStatusEnum,
    name="transfer_request_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class TransferRequest(Base):
    """
    Raised when a user requests an asset that is already allocated to someone else.
    Implements the "display who currently holds it, and offer a Transfer Request
    workflow" rule instead of silently failing the write. Wired up in Phase 3.
    """

    __tablename__ = "transfer_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    current_holder_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[TransferRequestStatusEnum] = mapped_column(
<<<<<<< HEAD
        transfer_status_pg_enum, nullable=False, default=TransferRequestStatusEnum.REQUESTED
=======
        transfer_status_pg_enum, nullable=False, default=TransferRequestStatusEnum.PENDING
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asset: Mapped["object"] = relationship("Asset")
    requested_by: Mapped["object"] = relationship("User", foreign_keys=[requested_by_id])
    current_holder: Mapped["object | None"] = relationship("User", foreign_keys=[current_holder_id])

    def __repr__(self) -> str:
        return f"<TransferRequest asset={self.asset_id} status={self.status}>"
