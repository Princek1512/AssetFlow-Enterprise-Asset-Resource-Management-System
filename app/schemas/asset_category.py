import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssetCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    custom_fields: dict | None = Field(
        default=None,
        description="Free-form per-category metadata schema, "
        'e.g. {"fields": [{"key": "cpu", "label": "CPU", "type": "string"}]}',
    )


class AssetCategoryUpdate(BaseModel):
    """All fields optional — PATCH semantics, only provided fields are changed."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    custom_fields: dict | None = None


class AssetCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    custom_fields: dict | None
    created_at: datetime
