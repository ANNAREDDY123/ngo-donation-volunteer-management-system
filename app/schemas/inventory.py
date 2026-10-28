
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.inventory import InventoryCategory, MovementType


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: InventoryCategory
    unit: str = Field(min_length=1, max_length=30)
    storage_location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "unit")
    @classmethod
    def clean_required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("storage_location", "description")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: InventoryCategory | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    storage_location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "unit")
    @classmethod
    def clean_required_text(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be empty")
        return value

    @field_validator("storage_location", "description")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class StockMovementCreate(BaseModel):
    quantity: int = Field(gt=0, le=1_000_000_000)
    reference: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("reference", "notes")
    @classmethod
    def clean_optional_text(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class InventoryItemResponse(BaseModel):
    id: int
    name: str
    category: InventoryCategory
    unit: str
    quantity: int
    storage_location: str | None
    description: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementResponse(BaseModel):
    id: int
    item_id: int
    movement_type: MovementType
    quantity: int
    quantity_after: int
    reference: str | None
    notes: str | None
    performed_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
