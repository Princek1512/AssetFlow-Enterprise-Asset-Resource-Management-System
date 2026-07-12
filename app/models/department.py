import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enums import DepartmentStatusEnum

dept_status_pg_enum = SAEnum(
    DepartmentStatusEnum,
    name="department_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    department_head_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_department_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[DepartmentStatusEnum] = mapped_column(
        dept_status_pg_enum, nullable=False, default=DepartmentStatusEnum.ACTIVE
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    department_head: Mapped["object | None"] = relationship(
        "User", foreign_keys=[department_head_id]
    )
    parent_department: Mapped["Department | None"] = relationship(
        "Department", remote_side=[id], foreign_keys=[parent_department_id]
    )
    members: Mapped[list["object"]] = relationship(
        "User", foreign_keys="[User.department_id]", back_populates="department"
    )

    def __repr__(self) -> str:
        return f"<Department {self.code} - {self.name}>"
