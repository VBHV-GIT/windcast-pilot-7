from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.elexon import (
    FuelHHIngestionResult,
    FuelHHRecord,
    IngestionAudit,
    WindforIngestionResult,
    WindforRecord,
)
from backend.app.services.elexon_client import ElexonAPIError, ElexonClientError

client = TestClient(app)


def _mock_ingestion_results():
    """Create sample mock records for Jan 1, 2026."""
    fuel_records = [
        FuelHHRecord(
            dataset="FUELHH",
            publishTime=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
            generation=10000.0,
        ),
        FuelHHRecord(
            dataset="FUELHH",
            publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
            startTime=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
            settlementDate="2026-01-01",
            settlementPeriod=2,
            fuelType="WIND",
            generation=12000.0,
        ),
    ]
    wind_records = [
        WindforRecord(
            dataset="WINDFOR",
            publishTime=datetime(2025, 12, 31, 16, 30, tzinfo=timezone.utc),
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            generation=11500.0,
        )
    ]

    fuel_res = FuelHHIngestionResult(
        records=fuel_records,
        audit=IngestionAudit(dataset="FUELHH", raw_records_received=2, records_retained=2),
    )
    wind_res = WindforIngestionResult(
        records=wind_records,
        audit=IngestionAudit(dataset="WINDFOR", raw_records_received=1, records_retained=1),
    )
    return fuel_res, wind_res


# =====================================================================
# 1. Successful Endpoint Responses
# =====================================================================


@patch("backend.app.routes.evaluation.ElexonClient")
def test_get_evaluation_endpoint_success(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    fuel_res, wind_res = _mock_ingestion_results()
    mock_instance.fetch_fuelhh.return_value = fuel_res
    mock_instance.fetch_windfor.return_value = wind_res

    response = client.get("/api/evaluation?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200

    data = response.json()
    assert "config" in data
    assert "metrics" in data
    assert "audit" in data
    assert "observations" in data
    assert data["audit"]["matched_intervals"] == 1
    assert data["metrics"]["mae_mw"] == 500.0  # |11500 - 11000|
    assert data["metrics"]["signed_bias_mw"] == 500.0


@patch("backend.app.routes.evaluation.ElexonClient")
def test_get_evaluation_summary_endpoint_success(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    fuel_res, wind_res = _mock_ingestion_results()
    mock_instance.fetch_fuelhh.return_value = fuel_res
    mock_instance.fetch_windfor.return_value = wind_res

    response = client.get("/api/evaluation/summary?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200

    data = response.json()
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-01-01"
    assert data["day_ahead_cutoff_time"] == "17:00"
    assert data["mae_mw"] == 500.0
    assert data["signed_bias_mw"] == 500.0
    assert data["matched_intervals"] == 1


@patch("backend.app.routes.evaluation.ElexonClient")
def test_get_evaluation_timeseries_endpoint_success(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    fuel_res, wind_res = _mock_ingestion_results()
    mock_instance.fetch_fuelhh.return_value = fuel_res
    mock_instance.fetch_windfor.return_value = wind_res

    response = client.get("/api/evaluation/timeseries?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200

    data = response.json()
    assert data["alignment"] == "HOURLY"
    assert data["total_observations"] == 1
    assert len(data["series"]) == 1
    obs = data["series"][0]
    assert obs["forecast_mw"] == 11500.0
    assert obs["actual_mw"] == 11000.0
    assert obs["error_mw"] == 500.0


@patch("backend.app.routes.evaluation.ElexonClient")
def test_get_evaluation_exclusions_endpoint_success(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    fuel_res, wind_res = _mock_ingestion_results()
    mock_instance.fetch_fuelhh.return_value = fuel_res
    mock_instance.fetch_windfor.return_value = wind_res

    response = client.get("/api/evaluation/exclusions?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200

    data = response.json()
    assert data["total_target_intervals"] == 24
    assert data["matched_intervals"] == 1
    # 23 intervals had neither forecast nor actual in our 1-interval mock
    assert data["missing_actual_count"] == 23
    assert data["missing_forecast_count"] == 23
    assert len(data["unmatched_intervals"]) == 23


# =====================================================================
# 2. Query Parameter Validation & Error Handling
# =====================================================================


def test_invalid_date_range_start_after_end():
    response = client.get("/api/evaluation?start_date=2026-01-10&end_date=2026-01-01")
    assert response.status_code == 400
    assert "start_date" in response.json()["detail"]


def test_date_range_exceeds_maximum_allowed():
    # 36 days span > 35 max days
    response = client.get("/api/evaluation?start_date=2026-01-01&end_date=2026-02-06")
    assert response.status_code == 400
    assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_invalid_cutoff_time_format():
    response = client.get("/api/evaluation?cutoff_time=25:99")
    assert response.status_code == 400
    assert "Invalid cutoff_time" in response.json()["detail"]


def test_invalid_alignment_enum():
    response = client.get("/api/evaluation?alignment=INVALID_STEP")
    assert response.status_code == 422


# =====================================================================
# 3. Empty Data & Zero Handling
# =====================================================================


@patch("backend.app.routes.evaluation.ElexonClient")
def test_empty_evaluation_returns_null_metrics(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    mock_instance.fetch_fuelhh.return_value = FuelHHIngestionResult(
        records=[], audit=IngestionAudit(dataset="FUELHH")
    )
    mock_instance.fetch_windfor.return_value = WindforIngestionResult(
        records=[], audit=IngestionAudit(dataset="WINDFOR")
    )

    response = client.get("/api/evaluation/summary?start_date=2026-01-01&end_date=2026-01-01")
    assert response.status_code == 200

    data = response.json()
    assert data["matched_intervals"] == 0
    assert data["coverage_rate_percent"] == 0.0
    assert data["mae_mw"] is None
    assert data["rmse_mw"] is None
    assert data["signed_bias_mw"] is None
    assert data["mape_percent"] is None
    assert data["wmape_percent"] is None


# =====================================================================
# 4. Upstream Error Handling (502 / 504)
# =====================================================================


@patch("backend.app.routes.evaluation.ElexonClient")
def test_upstream_elexon_api_error_returns_502(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    mock_instance.fetch_fuelhh.side_effect = ElexonAPIError(500, "Server Error", "https://data.elexon.co.uk")

    response = client.get("/api/evaluation")
    assert response.status_code == 502
    assert "Upstream Elexon API returned error status 500" in response.json()["detail"]


@patch("backend.app.routes.evaluation.ElexonClient")
def test_upstream_elexon_timeout_returns_504(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    mock_instance.fetch_fuelhh.side_effect = ElexonClientError("Connection timed out")

    response = client.get("/api/evaluation")
    assert response.status_code == 504
    assert "Failed to communicate with upstream Elexon API" in response.json()["detail"]


# =====================================================================
# 5. Caching Parameter Pass-Through
# =====================================================================


@patch("backend.app.routes.evaluation.ElexonClient")
def test_caching_parameter_propagated(mock_client_cls):
    mock_instance = mock_client_cls.return_value
    fuel_res, wind_res = _mock_ingestion_results()
    mock_instance.fetch_fuelhh.return_value = fuel_res
    mock_instance.fetch_windfor.return_value = wind_res

    client.get("/api/evaluation?use_cache=true")
    # Verify ElexonClient was instantiated with use_cache=True
    mock_client_cls.assert_called_with(use_cache=True)
