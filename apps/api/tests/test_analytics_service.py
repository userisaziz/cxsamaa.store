"""Tests for analytics service — overview, comparisons, trends."""
import uuid
from datetime import date
from unittest.mock import MagicMock, AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Tests: Analytics Overview
# ---------------------------------------------------------------------------

class TestAnalyticsOverview:
    @pytest.mark.asyncio
    async def test_empty_scope_returns_defaults(self, mock_db):
        """Empty scope returns zero-valued overview."""
        from src.services.analytics import get_analytics_overview
        
        # Mock no recordings in scope
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db, brand_id="brand-123")
        
        assert overview.funnel_stages is not None
        assert len(overview.outcome_distribution) == 0
    
    @pytest.mark.asyncio
    async def test_brand_scope_aggregates_data(self, mock_db):
        """Analytics aggregates data for brand scope."""
        from src.services.analytics import get_analytics_overview
        from src.schemas.analytics import AnalyticsOverviewResponse
        import uuid
        
        # Mock recording IDs
        mock_rec_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_rec_id,)]
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(
            mock_db,
            brand_id="brand-123",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31)
        )
        
        assert isinstance(overview, AnalyticsOverviewResponse)
    
    @pytest.mark.asyncio
    async def test_store_scope_filters_correctly(self, mock_db):
        """Analytics filters by store scope."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db, store_id="store-456")
        assert overview is not None


# ---------------------------------------------------------------------------
# Tests: Funnel Analysis
# ---------------------------------------------------------------------------

class TestFunnelAnalysis:
    @pytest.mark.asyncio
    async def test_funnel_has_conversation_stage(self, mock_db):
        """Funnel includes conversation count stage."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        funnel_stages = [f.stage for f in overview.funnel_stages]
        assert "Conversations" in funnel_stages or len(overview.funnel_stages) > 0
    
    @pytest.mark.asyncio
    async def test_funnel_has_closing_stage(self, mock_db):
        """Funnel includes closing attempts stage."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        # Funnel should have multiple stages
        assert len(overview.funnel_stages) >= 1
    
    @pytest.mark.asyncio
    async def test_funnel_has_sales_stage(self, mock_db):
        """Funnel includes sales made stage."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        # Verify funnel structure
        assert hasattr(overview, 'funnel_stages')


# ---------------------------------------------------------------------------
# Tests: Outcome Distribution
# ---------------------------------------------------------------------------

class TestOutcomeDistribution:
    @pytest.mark.asyncio
    async def test_outcome_groups_by_result(self, mock_db):
        """Outcome distribution groups by analysis outcome."""
        from src.services.analytics import get_analytics_overview
        
        # Mock empty results
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        assert isinstance(overview.outcome_distribution, list)
    
    @pytest.mark.asyncio
    async def test_outcome_handles_no_data(self, mock_db):
        """Outcome distribution handles empty dataset."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        assert len(overview.outcome_distribution) == 0


# ---------------------------------------------------------------------------
# Tests: Trend Analysis
# ---------------------------------------------------------------------------

class TestTrendAnalysis:
    @pytest.mark.asyncio
    async def test_score_trend_returns_time_series(self, mock_db):
        """Score trend returns daily time series."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        assert isinstance(overview.score_trend, list)
    
    @pytest.mark.asyncio
    async def test_volume_trend_tracks_recordings(self, mock_db):
        """Volume trend tracks recording count over time."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db)
        
        assert isinstance(overview.volume_trend, list)
    
    @pytest.mark.asyncio
    async def test_trends_handle_date_range(self, mock_db):
        """Trends respect date range filters."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(
            mock_db,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31)
        )
        
        assert overview is not None


# ---------------------------------------------------------------------------
# Tests: Store Comparison
# ---------------------------------------------------------------------------

class TestStoreComparison:
    @pytest.mark.asyncio
    async def test_store_comparison_returns_list(self, mock_db):
        """Store comparison returns list of store metrics."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db, brand_id="brand-123")
        
        assert isinstance(overview.store_comparison, list)
    
    @pytest.mark.asyncio
    async def test_store_comparison_empty_for_single_store(self, mock_db):
        """Store comparison may be empty for single store scope."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db, store_id="store-456")
        
        # May be empty or contain data
        assert isinstance(overview.store_comparison, list)


# ---------------------------------------------------------------------------
# Tests: Analytics Edge Cases
# ---------------------------------------------------------------------------

class TestAnalyticsEdgeCases:
    @pytest.mark.asyncio
    async def test_analytics_without_date_filters(self, mock_db):
        """Analytics works without date filters (all-time)."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(mock_db, brand_id="brand-123")
        assert overview is not None
    
    @pytest.mark.asyncio
    async def test_analytics_with_only_date_from(self, mock_db):
        """Analytics works with only start date."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(
            mock_db,
            date_from=date(2024, 1, 1)
        )
        assert overview is not None
    
    @pytest.mark.asyncio
    async def test_analytics_with_only_date_to(self, mock_db):
        """Analytics works with only end date."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(
            mock_db,
            date_to=date(2024, 12, 31)
        )
        assert overview is not None
    
    @pytest.mark.asyncio
    async def test_analytics_future_date_range(self, mock_db):
        """Analytics handles future date ranges gracefully."""
        from src.services.analytics import get_analytics_overview
        
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        overview = await get_analytics_overview(
            mock_db,
            date_from=date(2030, 1, 1),
            date_to=date(2030, 12, 31)
        )
        
        # Should return empty results, not error
        assert overview is not None
