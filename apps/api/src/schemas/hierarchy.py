"""Hierarchy schemas for brand-store-salesperson dropdown population."""
import uuid
from pydantic import BaseModel


class SalespersonHierarchyItem(BaseModel):
    """Minimal salesperson info for dropdown."""
    id: uuid.UUID
    name: str
    device_number: str | None = None

    model_config = {"from_attributes": True}


class StoreHierarchyItem(BaseModel):
    """Store with nested salespeople for cascading dropdowns."""
    id: uuid.UUID
    name: str
    location: str | None = None
    salespeople: list[SalespersonHierarchyItem] = []

    model_config = {"from_attributes": True}


class BrandHierarchyItem(BaseModel):
    """Brand with nested stores and salespeople."""
    id: uuid.UUID
    name: str
    description: str | None = None
    stores: list[StoreHierarchyItem] = []

    model_config = {"from_attributes": True}


class HierarchyResponse(BaseModel):
    """Complete brand-store-salesperson hierarchy."""
    brands: list[BrandHierarchyItem]
