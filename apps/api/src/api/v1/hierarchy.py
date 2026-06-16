"""Hierarchy API endpoints for dropdown population."""
from fastapi import APIRouter, Depends

from src.api.deps import require_authenticated
from src.database import get_db
from src.models.user import User
from src.schemas.hierarchy import HierarchyResponse
from src.services.hierarchy import get_full_hierarchy

router = APIRouter(prefix="/hierarchy", tags=["Hierarchy"])


@router.get("", response_model=HierarchyResponse)
async def get_hierarchy(
    db = Depends(get_db),
    _user: User = Depends(require_authenticated),
):
    """Get complete brand → store → salesperson hierarchy.
    
    Returns nested structure optimized for cascading dropdowns:
    - Brands at top level
    - Each brand contains its stores
    - Each store contains its salespeople
    
    Single API call replaces 3 separate calls (brands, stores, salespeople).
    """
    return await get_full_hierarchy(db)
