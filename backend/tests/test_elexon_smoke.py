import os
import pytest
from backend.app.services.elexon_client import ElexonClient

# Only run this smoke test if explicitly requested via environment variable:
# e.g. RUN_LIVE_TESTS=1 pytest backend/tests/test_elexon_smoke.py
LIVE_TEST_ENABLED = os.environ.get("RUN_LIVE_TESTS", "0").lower() in ("1", "true", "yes")

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.skipif(
        not LIVE_TEST_ENABLED,
        reason="Live API smoke test disabled by default. Set RUN_LIVE_TESTS=1 to enable.",
    ),
]


def test_live_fuelhh_smoke():
    """Live smoke test fetching 1 day of real FUELHH data from Elexon."""
    client = ElexonClient(use_cache=False)
    result = client.fetch_fuelhh(start_date="2026-01-01", end_date="2026-01-01")

    assert len(result.records) == 48  # 48 settlement periods on 2026-01-01
    sample = result.records[0]
    assert sample.dataset == "FUELHH"
    assert sample.fuel_type == "WIND"
    assert sample.settlement_date == "2026-01-01"
    assert 1 <= sample.settlement_period <= 48
    assert sample.generation >= 0.0


def test_live_windfor_smoke():
    """Live smoke test fetching a 12-hour publication batch of real WINDFOR data."""
    client = ElexonClient(use_cache=False)
    result = client.fetch_windfor(
        publish_from="2026-01-01T00:00:00Z",
        publish_to="2026-01-01T12:00:00Z",
    )

    assert len(result.records) > 0
    sample = result.records[0]
    assert sample.dataset == "WINDFOR"
    assert sample.generation >= 0.0
    assert sample.publish_time is not None
    assert sample.start_time is not None
