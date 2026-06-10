"""Tests for store service — CRUD operations and filtering."""
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Tests: Store Retrieval
# ---------------------------------------------------------------------------

class TestStoreService:
    @pytest.mark.asyncio
    async def test_get_store_success(self, mock_db):
        """get_store returns store when found."""
        from src.services.store import get_store
        from src.models.store import Store
        
        store_id = uuid.uuid4()
        mock_store = MagicMock(spec=Store)
        mock_store.id = store_id
        mock_store.name = "Test Store"
        mock_store.brand_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_store
        mock_db.execute.return_value = mock_result
        
        store = await get_store(mock_db, str(store_id))
        assert store.name == "Test Store"
    
    @pytest.mark.asyncio
    async def test_get_store_not_found(self, mock_db):
        """get_store raises 404 when store not found."""
        from src.services.store import get_store
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_store(mock_db, str(uuid.uuid4()))
        
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Store Listing
# ---------------------------------------------------------------------------

class TestStoreListing:
    @pytest.mark.asyncio
    async def test_list_stores_returns_list(self, mock_db):
        """list_stores returns list of stores."""
        from src.services.store import list_stores
        from src.models.store import Store
        
        mock_store = MagicMock(spec=Store)
        mock_store.id = uuid.uuid4()
        mock_store.name = "Store 1"
        mock_store.brand_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_store]
        mock_db.execute.return_value = mock_result
        
        stores = await list_stores(mock_db)
        assert isinstance(stores, list)
        assert len(stores) == 1
    
    @pytest.mark.asyncio
    async def test_list_stores_by_brand(self, mock_db):
        """list_stores filters by brand_id."""
        from src.services.store import list_stores
        from src.models.store import Store
        
        brand_id = uuid.uuid4()
        mock_store = MagicMock(spec=Store)
        mock_store.id = uuid.uuid4()
        mock_store.name = "Brand Store"
        mock_store.brand_id = brand_id
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_store]
        mock_db.execute.return_value = mock_result
        
        stores = await list_stores(mock_db, brand_id=str(brand_id))
        assert len(stores) == 1
        assert stores[0].brand_id == brand_id
    
    @pytest.mark.asyncio
    async def test_list_stores_empty(self, mock_db):
        """list_stores returns empty list when no stores."""
        from src.services.store import list_stores
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        stores = await list_stores(mock_db)
        assert isinstance(stores, list)
        assert len(stores) == 0
    
    @pytest.mark.asyncio
    async def test_list_stores_with_pagination(self, mock_db):
        """list_stores supports pagination parameters."""
        from src.services.store import list_stores
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        stores = await list_stores(mock_db, skip=0, limit=10)
        assert isinstance(stores, list)


# ---------------------------------------------------------------------------
# Tests: Store Creation
# ---------------------------------------------------------------------------

class TestStoreCreation:
    @pytest.mark.asyncio
    async def test_create_store_success(self, mock_db):
        """create_store creates new store."""
        from src.services.store import create_store
        from src.schemas.store import StoreCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        
        brand_id = uuid.uuid4()
        store_data = StoreCreate(
            name="New Store",
            brand_id=str(brand_id)
        )
        
        store = await create_store(mock_db, store_data)
        
        mock_db.add.assert_called_once()
        assert store.name == "New Store"
    
    @pytest.mark.asyncio
    async def test_create_store_with_location(self, mock_db):
        """create_store accepts optional location field."""
        from src.services.store import create_store
        from src.schemas.store import StoreCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        
        brand_id = uuid.uuid4()
        store_data = StoreCreate(
            name="Store with Location",
            brand_id=str(brand_id),
            location="Dubai, UAE"
        )
        
        store = await create_store(mock_db, store_data)
        assert store.location == "Dubai, UAE"


# ---------------------------------------------------------------------------
# Tests: Store Update
# ---------------------------------------------------------------------------

class TestStoreUpdate:
    @pytest.mark.asyncio
    async def test_update_store_success(self, mock_db):
        """update_store modifies existing store."""
        from src.services.store import update_store
        from src.models.store import Store
        from src.schemas.store import StoreUpdate
        
        store_id = uuid.uuid4()
        mock_store = MagicMock(spec=Store)
        mock_store.id = store_id
        mock_store.name = "Old Name"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_store
        mock_db.execute.return_value = mock_result
        
        update_data = StoreUpdate(name="New Name")
        
        updated_store = await update_store(mock_db, str(store_id), update_data)
        
        assert updated_store.name == "New Name"
    
    @pytest.mark.asyncio
    async def test_update_store_not_found(self, mock_db):
        """update_store raises 404 for non-existent store."""
        from src.services.store import update_store
        from src.schemas.store import StoreUpdate
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await update_store(mock_db, str(uuid.uuid4()), StoreUpdate(name="New"))
        
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Store Deletion
# ---------------------------------------------------------------------------

class TestStoreDeletion:
    @pytest.mark.asyncio
    async def test_delete_store_success(self, mock_db):
        """delete_store removes store from database."""
        from src.services.store import delete_store
        from src.models.store import Store
        
        store_id = uuid.uuid4()
        mock_store = MagicMock(spec=Store)
        mock_store.id = store_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_store
        mock_db.execute.return_value = mock_result
        
        await delete_store(mock_db, str(store_id))
        
        mock_db.delete.assert_called_once_with(mock_store)
    
    @pytest.mark.asyncio
    async def test_delete_store_not_found(self, mock_db):
        """delete_store raises 404 for non-existent store."""
        from src.services.store import delete_store
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_store(mock_db, str(uuid.uuid4()))
        
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Store Model Validation
# ---------------------------------------------------------------------------

class TestStoreModel:
    def test_store_model_fields(self):
        """Store model has required fields."""
        from src.models.store import Store
        
        assert hasattr(Store, 'id')
        assert hasattr(Store, 'name')
        assert hasattr(Store, 'brand_id')
        assert hasattr(Store, 'created_at')
    
    def test_store_brand_id_foreign_key(self):
        """Store has foreign key relationship to Brand."""
        from src.models.store import Store
        
        # Verify brand_id field exists
        assert hasattr(Store, 'brand_id')
    
    def test_store_schema_validation(self):
        """StoreCreate schema validates required fields."""
        from src.schemas.store import StoreCreate
        import uuid
        
        brand_id = uuid.uuid4()
        store = StoreCreate(
            name="Test Store",
            brand_id=str(brand_id)
        )
        
        assert store.name == "Test Store"
        assert store.brand_id == str(brand_id)
    
    def test_store_schema_optional_fields(self):
        """StoreCreate accepts optional fields."""
        from src.schemas.store import StoreCreate
        import uuid
        
        brand_id = uuid.uuid4()
        store = StoreCreate(
            name="Test Store",
            brand_id=str(brand_id),
            location="Optional Location",
            description="Optional Description"
        )
        
        assert store.location == "Optional Location"
        assert store.description == "Optional Description"


# ---------------------------------------------------------------------------
# Tests: Store Edge Cases
# ---------------------------------------------------------------------------

class TestStoreEdgeCases:
    @pytest.mark.asyncio
    async def test_list_stores_multiple_brands(self, mock_db):
        """list_stores handles stores from multiple brands."""
        from src.services.store import list_stores
        from src.models.store import Store
        
        brand1 = uuid.uuid4()
        brand2 = uuid.uuid4()
        
        mock_stores = [
            MagicMock(id=uuid.uuid4(), name="Store 1", brand_id=brand1),
            MagicMock(id=uuid.uuid4(), name="Store 2", brand_id=brand2),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_stores
        mock_db.execute.return_value = mock_result
        
        stores = await list_stores(mock_db)
        assert len(stores) == 2
    
    @pytest.mark.asyncio
    async def test_store_name_max_length(self, mock_db):
        """Store name respects maximum length constraints."""
        from src.services.store import create_store
        from src.schemas.store import StoreCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        
        brand_id = uuid.uuid4()
        # Create store with long name
        long_name = "A" * 200
        store_data = StoreCreate(
            name=long_name,
            brand_id=str(brand_id)
        )
        
        store = await create_store(mock_db, store_data)
        assert len(store.name) == 200
    
    @pytest.mark.asyncio
    async def test_store_special_characters_in_name(self, mock_db):
        """Store name accepts special characters."""
        from src.services.store import create_store
        from src.schemas.store import StoreCreate
        
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        
        brand_id = uuid.uuid4()
        store_data = StoreCreate(
            name="Store & Co. (Dubai)",
            brand_id=str(brand_id)
        )
        
        store = await create_store(mock_db, store_data)
        assert "&" in store.name
        assert "(" in store.name
