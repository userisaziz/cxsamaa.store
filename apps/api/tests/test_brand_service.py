"""Tests for brand service — CRUD operations and listing."""
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Tests: Brand Retrieval
# ---------------------------------------------------------------------------

class TestBrandService:
    @pytest.mark.asyncio
    async def test_get_brand_success(self, mock_db):
        """get_brand returns brand when found."""
        from src.services.brand import get_brand
        from src.models.brand import Brand
        
        brand_id = uuid.uuid4()
        mock_brand = MagicMock(spec=Brand)
        mock_brand.id = brand_id
        mock_brand.name = "Test Brand"
        mock_brand.description = "Test Description"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_brand
        mock_db.execute.return_value = mock_result
        
        brand = await get_brand(mock_db, str(brand_id))
        assert brand.name == "Test Brand"
    
    @pytest.mark.asyncio
    async def test_get_brand_not_found(self, mock_db):
        """get_brand raises 404 when brand not found."""
        from src.services.brand import get_brand
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_brand(mock_db, str(uuid.uuid4()))
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_brand_invalid_uuid(self, mock_db):
        """get_brand handles invalid UUID format."""
        from src.services.brand import get_brand
        
        with pytest.raises((HTTPException, ValueError)):
            await get_brand(mock_db, "not-a-uuid")


# ---------------------------------------------------------------------------
# Tests: Brand Listing
# ---------------------------------------------------------------------------

class TestBrandListing:
    @pytest.mark.asyncio
    async def test_list_brands_returns_list(self, mock_db):
        """list_brands returns list of brands."""
        from src.services.brand import list_brands
        from src.models.brand import Brand
        
        mock_brand = MagicMock(spec=Brand)
        mock_brand.id = uuid.uuid4()
        mock_brand.name = "Brand 1"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_brand]
        mock_db.execute.return_value = mock_result
        
        brands = await list_brands(mock_db)
        assert isinstance(brands, list)
        assert len(brands) == 1
    
    @pytest.mark.asyncio
    async def test_list_brands_empty(self, mock_db):
        """list_brands returns empty list when no brands."""
        from src.services.brand import list_brands
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        brands = await list_brands(mock_db)
        assert isinstance(brands, list)
        assert len(brands) == 0
    
    @pytest.mark.asyncio
    async def test_list_brands_with_pagination(self, mock_db):
        """list_brands supports pagination parameters."""
        from src.services.brand import list_brands
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Test with pagination params
        brands = await list_brands(mock_db, skip=0, limit=10)
        assert isinstance(brands, list)


# ---------------------------------------------------------------------------
# Tests: Brand Creation
# ---------------------------------------------------------------------------

class TestBrandCreation:
    @pytest.mark.asyncio
    async def test_create_brand_success(self, mock_db):
        """create_brand creates new brand."""
        from src.services.brand import create_brand
        from src.schemas.brand import BrandCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        brand_data = BrandCreate(
            name="New Brand",
            description="A test brand"
        )
        
        # Mock the add operation
        mock_db.add = MagicMock()
        
        brand = await create_brand(mock_db, brand_data)
        
        # Verify brand was added to session
        mock_db.add.assert_called_once()
        assert brand.name == "New Brand"
    
    @pytest.mark.asyncio
    async def test_create_brand_minimal_fields(self, mock_db):
        """create_brand works with only required fields."""
        from src.services.brand import create_brand
        from src.schemas.brand import BrandCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        
        brand_data = BrandCreate(name="Minimal Brand")
        
        brand = await create_brand(mock_db, brand_data)
        assert brand.name == "Minimal Brand"


# ---------------------------------------------------------------------------
# Tests: Brand Update
# ---------------------------------------------------------------------------

class TestBrandUpdate:
    @pytest.mark.asyncio
    async def test_update_brand_success(self, mock_db):
        """update_brand modifies existing brand."""
        from src.services.brand import update_brand
        from src.models.brand import Brand
        from src.schemas.brand import BrandUpdate
        
        brand_id = uuid.uuid4()
        mock_brand = MagicMock(spec=Brand)
        mock_brand.id = brand_id
        mock_brand.name = "Old Name"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_brand
        mock_db.execute.return_value = mock_result
        
        update_data = BrandUpdate(name="New Name")
        
        updated_brand = await update_brand(mock_db, str(brand_id), update_data)
        
        assert updated_brand.name == "New Name"
    
    @pytest.mark.asyncio
    async def test_update_brand_not_found(self, mock_db):
        """update_brand raises 404 for non-existent brand."""
        from src.services.brand import update_brand
        from src.schemas.brand import BrandUpdate
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await update_brand(mock_db, str(uuid.uuid4()), BrandUpdate(name="New"))
        
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Brand Deletion
# ---------------------------------------------------------------------------

class TestBrandDeletion:
    @pytest.mark.asyncio
    async def test_delete_brand_success(self, mock_db):
        """delete_brand removes brand from database."""
        from src.services.brand import delete_brand
        from src.models.brand import Brand
        
        brand_id = uuid.uuid4()
        mock_brand = MagicMock(spec=Brand)
        mock_brand.id = brand_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_brand
        mock_db.execute.return_value = mock_result
        
        await delete_brand(mock_db, str(brand_id))
        
        # Verify brand was deleted
        mock_db.delete.assert_called_once_with(mock_brand)
    
    @pytest.mark.asyncio
    async def test_delete_brand_not_found(self, mock_db):
        """delete_brand raises 404 for non-existent brand."""
        from src.services.brand import delete_brand
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_brand(mock_db, str(uuid.uuid4()))
        
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Brand Model Validation
# ---------------------------------------------------------------------------

class TestBrandModel:
    def test_brand_model_fields(self):
        """Brand model has required fields."""
        from src.models.brand import Brand
        
        assert hasattr(Brand, 'id')
        assert hasattr(Brand, 'name')
        assert hasattr(Brand, 'description')
        assert hasattr(Brand, 'created_at')
    
    def test_brand_name_required(self):
        """Brand name is a required field."""
        from src.schemas.brand import BrandCreate
        
        # Name should be required in schema
        schema = BrandCreate.__fields__ if hasattr(BrandCreate, '__fields__') else BrandCreate.model_fields
        assert 'name' in schema
    
    def test_brand_description_optional(self):
        """Brand description is optional."""
        from src.schemas.brand import BrandCreate
        
        # Should be able to create brand without description
        brand = BrandCreate(name="Test")
        assert brand.name == "Test"
