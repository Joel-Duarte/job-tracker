from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.analytics import get_funnel_performance_metrics


@pytest.mark.asyncio
async def test_get_funnel_performance_metrics_unit():
    mock_db = AsyncMock()

    # Create mock execution results for intake, app, and event queries
    mock_res_intake = MagicMock()
    mock_res_intake.scalars.return_value.all.return_value = []

    mock_res_apps = MagicMock()
    mock_res_apps.all.return_value = []

    mock_res_events = MagicMock()
    mock_res_events.all.return_value = []

    mock_db.execute.side_effect = [mock_res_intake, mock_res_apps, mock_res_events]

    result = await get_funnel_performance_metrics(
        mock_db, period="weekly", num_periods=4
    )
    assert result.period_type == "weekly"
    assert len(result.chart_data) == 4
    assert len(result.table_data) == 4
    assert "intakes" in result.summary_kpis
    assert result.summary_kpis["intakes"].value == 0
