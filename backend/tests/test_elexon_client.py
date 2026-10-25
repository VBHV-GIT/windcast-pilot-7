import json
from datetime import date, datetime, timedelta, timezone
from typing import List

import httpx
import pytest

from backend.app.schemas.elexon import FuelHHRecord, WindforRecord
from backend.app.services.elexon_client import (
    ElexonAPIError,
    ElexonClient,
    ElexonClientError,
    generate_fuelhh_date_chunks,
    generate_windfor_date_chunks,
)


# =====================================================================
# 1. Chunking Tests (1, 7, 8, 31, 32 days)
# =====================================================================


def test_chunking_1_day():
    chunks = generate_fuelhh_date_chunks("2026-01-01", "2026-01-01")
    assert len(chunks) == 1
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 1))
    assert (chunks[0][1] - chunks[0][0]).days + 1 == 1


def test_chunking_7_days():
    chunks = generate_fuelhh_date_chunks("2026-01-01", "2026-01-07")
    assert len(chunks) == 1
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
    assert (chunks[0][1] - chunks[0][0]).days + 1 == 7


def test_chunking_8_days():
    chunks = generate_fuelhh_date_chunks("2026-01-01", "2026-01-08")
    assert len(chunks) == 2
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
    assert chunks[1] == (date(2026, 1, 8), date(2026, 1, 8))
    # Boundary checks: zero overlap, zero gaps
    assert chunks[1][0] == chunks[0][1] + timedelta(days=1)


def test_chunking_31_days_january():
    chunks = generate_fuelhh_date_chunks("2026-01-01", "2026-01-31")
    assert len(chunks) == 5

    # Check each chunk size <= 7 days inclusive
    all_dates = []
    for i, (start, end) in enumerate(chunks):
        span = (end - start).days + 1
        assert span <= 7, f"Chunk {i} exceeded 7 days: {span}"
        if i > 0:
            assert start == chunks[i - 1][1] + timedelta(days=1), f"Gap or overlap at chunk {i}"
        curr = start
        while curr <= end:
            all_dates.append(curr)
            curr += timedelta(days=1)

    assert len(all_dates) == 31
    assert all_dates[0] == date(2026, 1, 1)
    assert all_dates[-1] == date(2026, 1, 31)
    # Ensure no duplicates
    assert len(set(all_dates)) == 31


def test_chunking_32_days_windfor():
    # 2025-12-31 to 2026-01-31 (32 calendar days)
    start_dt = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

    chunks = generate_windfor_date_chunks(start_dt, end_dt)
    assert len(chunks) == 5

    # Verify calendar days per chunk <= 7
    all_dates = []
    for i, (c_start, c_end) in enumerate(chunks):
        assert c_start.tzinfo == timezone.utc
        assert c_end.tzinfo == timezone.utc
        span_days = (c_end.date() - c_start.date()).days + 1
        assert span_days <= 7, f"WINDFOR chunk {i} spanned {span_days} calendar days"

        if i > 0:
            prev_end = chunks[i - 1][1]
            assert c_start.date() == prev_end.date() + timedelta(days=1), f"Gap/overlap between {prev_end} and {c_start}"

        curr = c_start.date()
        while curr <= c_end.date():
            all_dates.append(curr)
            curr += timedelta(days=1)

    assert len(all_dates) == 32
    assert len(set(all_dates)) == 32
    assert all_dates[0] == date(2025, 12, 31)
    assert all_dates[-1] == date(2026, 1, 31)


def test_chunking_invalid_range():
    with pytest.raises(ValueError, match="cannot be after"):
        generate_fuelhh_date_chunks("2026-01-05", "2026-01-01")

    with pytest.raises(ValueError, match="cannot be after"):
        generate_windfor_date_chunks("2026-01-05T00:00:00Z", "2026-01-01T00:00:00Z")


# =====================================================================
# 2. Filtering & Schema Validation Tests
# =====================================================================


def test_fuelhh_filtering_and_validation():
    mock_payload = {
        "data": [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 14200,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "CCGT",  # Non-WIND: should be filtered out
                "generation": 8500,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 99,  # Invalid SP (>50): malformed
                "fuelType": "WIND",
                "generation": 500,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    client = ElexonClient(transport=httpx.MockTransport(handler), use_cache=False)
    result = client.fetch_fuelhh("2026-01-01", "2026-01-01")

    assert len(result.records) == 1
    assert result.records[0].fuel_type == "WIND"
    assert result.records[0].generation == 14200.0
    assert result.audit.raw_records_received == 3
    assert result.audit.records_retained == 1
    assert result.audit.non_wind_records_excluded == 1
    assert result.audit.malformed_records_excluded == 1


def test_windfor_preservation_and_validation():
    mock_payload = {
        "data": [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T02:30:00Z",
                "startTime": "2026-01-01T03:00:00Z",
                "generation": 18500,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T02:30:00Z",
                "startTime": "invalid-datetime",  # Malformed
                "generation": 12000,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    client = ElexonClient(transport=httpx.MockTransport(handler), use_cache=False)
    result = client.fetch_windfor("2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z")

    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.dataset == "WINDFOR"
    assert rec.publish_time == datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    assert rec.start_time == datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
    assert rec.generation == 18500.0
    assert result.audit.raw_records_received == 2
    assert result.audit.records_retained == 1
    assert result.audit.malformed_records_excluded == 1


# =====================================================================
# 3. Deduplication & Revision Tracking Tests
# =====================================================================


def test_fuelhh_deduplication_retains_latest_revision():
    mock_payload = {
        "data": [
            # Revision 1 (initial publication at 00:30)
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 14000,
            },
            # Revision 2 (settlement revised figure published at 04:00)
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T04:00:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 14250,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    client = ElexonClient(transport=httpx.MockTransport(handler), use_cache=False)
    result = client.fetch_fuelhh("2026-01-01", "2026-01-01")

    assert len(result.records) == 1
    # Latest revision retained:
    assert result.records[0].generation == 14250
    assert result.records[0].publish_time == datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
    assert result.audit.duplicate_records_excluded == 1
    assert result.audit.records_retained == 1


def test_windfor_deduplication_on_composite_key():
    mock_payload = {
        "data": [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T04:30:00Z",
                "startTime": "2026-01-01T10:00:00Z",
                "generation": 16000,
            },
            # Exact duplicate record
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T04:30:00Z",
                "startTime": "2026-01-01T10:00:00Z",
                "generation": 16000,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    client = ElexonClient(transport=httpx.MockTransport(handler), use_cache=False)
    result = client.fetch_windfor("2026-01-01T00:00:00Z", "2026-01-01T12:00:00Z")

    assert len(result.records) == 1
    assert result.audit.duplicate_records_excluded == 1
    assert result.audit.records_retained == 1


# =====================================================================
# 4. HTTP Retries & Error Handling Tests
# =====================================================================


def test_retry_on_transient_503_success():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "dataset": "FUELHH",
                        "publishTime": "2026-01-01T01:00:00Z",
                        "startTime": "2026-01-01T00:00:00Z",
                        "settlementDate": "2026-01-01",
                        "settlementPeriod": 1,
                        "fuelType": "WIND",
                        "generation": 13000,
                    }
                ]
            },
        )

    client = ElexonClient(
        transport=httpx.MockTransport(handler),
        max_retries=3,
        retry_delay=0.001,
        use_cache=False,
    )
    result = client.fetch_fuelhh("2026-01-01", "2026-01-01")

    assert calls == 3
    assert len(result.records) == 1
    assert result.records[0].generation == 13000


def test_retry_exhaustion_raises_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = ElexonClient(
        transport=httpx.MockTransport(handler),
        max_retries=2,
        retry_delay=0.001,
        use_cache=False,
    )

    with pytest.raises(ElexonAPIError) as exc_info:
        client.fetch_fuelhh("2026-01-01", "2026-01-01")

    assert exc_info.value.status_code == 500


def test_network_timeout_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = ElexonClient(
        transport=httpx.MockTransport(handler),
        max_retries=1,
        retry_delay=0.001,
        use_cache=False,
    )

    with pytest.raises(ElexonClientError, match="Network error"):
        client.fetch_fuelhh("2026-01-01", "2026-01-01")
