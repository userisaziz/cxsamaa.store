"""Hierarchy service for fetching brand-store-salesperson tree."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.brand import Brand
from src.models.store import Store
from src.models.salesperson import Salesperson
from src.schemas.hierarchy import (
    BrandHierarchyItem,
    HierarchyResponse,
    SalespersonHierarchyItem,
    StoreHierarchyItem,
)


async def get_full_hierarchy(db: AsyncSession) -> HierarchyResponse:
    """Fetch complete brand → store → salesperson hierarchy in one query.
    
    Uses eager loading to avoid N+1 query problem.
    Returns nested structure optimized for cascading dropdowns.
    """
    # Single query with eager loading of relationships
    # Note: Can only order by Brand fields in main query; stores/salespeople
    # are loaded via separate queries by selectinload
    query = (
        select(Brand)
        .options(
            selectinload(Brand.stores).selectinload(Store.salespeople)
        )
        .order_by(Brand.name.asc())
    )
    
    result = await db.execute(query)
    brands = result.scalars().all()
    
    # Build hierarchical response
    brand_items = []
    for brand in brands:
        store_items = []
        # Sort stores by name
        sorted_stores = sorted(brand.stores, key=lambda s: s.name)
        for store in sorted_stores:
            # Sort salespeople by name
            sorted_salespeople = sorted(store.salespeople, key=lambda sp: sp.name)
            salesperson_items = [
                SalespersonHierarchyItem(
                    id=salesperson.id,
                    name=salesperson.name,
                    device_number=salesperson.device_number,
                )
                for salesperson in sorted_salespeople
            ]
            store_items.append(
                StoreHierarchyItem(
                    id=store.id,
                    name=store.name,
                    location=store.location,
                    salespeople=salesperson_items,
                )
            )
        
        brand_items.append(
            BrandHierarchyItem(
                id=brand.id,
                name=brand.name,
                description=brand.description,
                stores=store_items,
            )
        )
    
    return HierarchyResponse(brands=brand_items)
