from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.schemas.analysis import (
    AccuracyMetrics,
    EvaluationAudit,
    EvaluationConfig,
    EvaluationResult,
    IntervalExclusion,
    MatchedObservation,
    ResolutionAlignment,
)
from backend.app.schemas.elexon import IngestionAudit
from backend.app.services.elexon_client import (
    ElexonAPIError,
    ElexonClient,
    ElexonClientError,
)
from backend.app.services.forecast_evaluator import ForecastEvaluator

router = APIRouter(prefix="/evaluation", tags=["Forecast Evaluation"])

MAX_ALLOWED_DAYS = 35


# ---------------------------------------------------------------------------
# Response Models for Specialized Endpoints
# ---------------------------------------------------------------------------


class EvaluationSummaryResponse(BaseModel):
    """Key performance indicators and coverage summary."""
    start_date: date
    end_date: date
    day_ahead_cutoff_time: str
    alignment: ResolutionAlignment
    total_target_intervals: int
    matched_intervals: int
    coverage_rate_percent: float
    mae_mw: Optional[float] = Field(None, description="Mean Absolute Error in MW (null if no matched intervals)")
    rmse_mw: Optional[float] = Field(None, description="Root Mean Square Error in MW (null if no matched intervals)")
    signed_bias_mw: Optional[float] = Field(None, description="Signed Bias in MW: mean(Forecast - Actual) (null if no matched intervals)")
    mape_percent: Optional[float] = Field(None, description="Mean Absolute Percentage Error (null if actuals <= epsilon)")
    wmape_percent: Optional[float] = Field(None, description="Weighted MAPE (null if total actual == 0)")
    total_forecast_energy_mwh: Optional[float] = None
    total_actual_energy_mwh: Optional[float] = None
    mape_valid_samples: int = 0
    mape_excluded_zero_samples: int = 0


class TimeSeriesResponse(BaseModel):
    """Time-series series of matched forecast and actual observations for frontend charting."""
    alignment: ResolutionAlignment
    total_observations: int
    series: List[MatchedObservation]


class ExclusionsResponse(BaseModel):
    """Detailed audit report of exclusions, missing intervals, and ingestion stats."""
    total_target_intervals: int
    matched_intervals: int
    coverage_rate_percent: float
    missing_actual_count: int
    missing_forecast_count: int
    excluded_non_target_delivery_records: int
    excluded_retrospective_forecasts: int
    excluded_post_cutoff_forecasts: int
    unmatched_intervals: List[IntervalExclusion]
    ingestion_audit_actuals: Optional[IngestionAudit] = None
    ingestion_audit_forecasts: Optional[IngestionAudit] = None


# ---------------------------------------------------------------------------
# Shared Dependency for Query Parameters & Pipeline Execution
# ---------------------------------------------------------------------------


def parse_and_validate_params(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="Delivery start date inclusive (YYYY-MM-DD)",
        openapi_examples={"jan_start": {"summary": "Jan 1, 2026", "value": "2026-01-01"}},
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Delivery end date inclusive (YYYY-MM-DD)",
        openapi_examples={"jan_end": {"summary": "Jan 31, 2026", "value": "2026-01-31"}},
    ),
    cutoff_time: str = Query(
        default="17:00",
        description="Day-ahead cutoff time on day D-1 in UTC (HH:MM or HH:MM:SS). Default 17:00 is a pilot assumption.",
        openapi_examples={"pilot_default": {"summary": "17:00 UTC", "value": "17:00"}},
    ),
    alignment: ResolutionAlignment = Query(
        default=ResolutionAlignment.HOURLY,
        description="Resolution alignment: HOURLY (physically exact average) or HALF_HOURLY (broadcast).",
    ),
    use_cache: bool = Query(
        default=False,
        description="Whether to use cached raw Elexon API responses.",
    ),
) -> Tuple[EvaluationConfig, bool]:
    """Validate query parameters and construct EvaluationConfig."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_date ({start_date}) cannot be after end_date ({end_date})",
        )

    day_span = (end_date - start_date).days + 1
    if day_span > MAX_ALLOWED_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested date range ({day_span} days) exceeds maximum allowed limit of {MAX_ALLOWED_DAYS} days",
        )

    # Parse cutoff time
    try:
        parts = cutoff_time.strip().split(":")
        if len(parts) == 2:
            hour, minute = int(parts[0]), int(parts[1])
            cutoff_t = time(hour, minute, 0)
        elif len(parts) == 3:
            hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            cutoff_t = time(hour, minute, second)
        else:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cutoff_time '{cutoff_time}'. Expected format HH:MM or HH:MM:SS (e.g. 17:00 or 12:00:00)",
        )

    config = EvaluationConfig(
        start_date=start_date,
        end_date=end_date,
        day_ahead_cutoff_time=cutoff_t,
        alignment=alignment,
    )

    return config, use_cache


def run_evaluation_pipeline(
    config: EvaluationConfig,
    use_cache: bool,
    client: Optional[ElexonClient] = None,
) -> EvaluationResult:
    """Execute ingestion and evaluation pipeline with upstream error handling."""
    if client is None:
        client = ElexonClient(use_cache=use_cache)

    try:
        # 1. Fetch FUELHH actuals
        fuelhh_res = client.fetch_fuelhh(
            start_date=config.start_date,
            end_date=config.end_date,
            fuel_type="WIND",
        )

        # 2. Fetch WINDFOR forecasts (including D-1 lookback for start_date day-ahead cutoff)
        lookback_date = config.start_date - timedelta(days=1)
        publish_from = datetime.combine(lookback_date, time.min, tzinfo=timezone.utc)
        publish_to = datetime.combine(config.end_date, time(23, 59, 59), tzinfo=timezone.utc)

        windfor_res = client.fetch_windfor(
            publish_from=publish_from,
            publish_to=publish_to,
        )

    except ElexonAPIError as api_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream Elexon API returned error status {api_err.status_code}",
        )
    except ElexonClientError as client_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Failed to communicate with upstream Elexon API (timeout or connection error)",
        )

    # 3. Evaluate observations
    return ForecastEvaluator.evaluate(
        fuelhh_records=fuelhh_res.records,
        windfor_records=windfor_res.records,
        config=config,
        ingestion_audit_actuals=fuelhh_res.audit,
        ingestion_audit_forecasts=windfor_res.audit,
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=EvaluationResult,
    summary="Complete Wind Generation Forecast Evaluation",
    description=(
        "Reconstructs day-ahead wind forecasts and evaluates their accuracy against actual outturn "
        "for the specified delivery date range. Returns metrics, audit logs, and paired observations."
    ),
)
def get_evaluation(params: Tuple[EvaluationConfig, bool] = Depends(parse_and_validate_params)):
    config, use_cache = params
    return run_evaluation_pipeline(config, use_cache)


@router.get(
    "/summary",
    response_model=EvaluationSummaryResponse,
    summary="Key Forecast Accuracy Metrics Summary",
    description="Returns high-level summary KPIs (MAE, RMSE, Signed Bias, MAPE, WMAPE, and coverage). Unavailable metrics are returned as null.",
)
def get_evaluation_summary(params: Tuple[EvaluationConfig, bool] = Depends(parse_and_validate_params)):
    config, use_cache = params
    result = run_evaluation_pipeline(config, use_cache)

    m = result.metrics
    cutoff_str = config.day_ahead_cutoff_time.strftime("%H:%M")

    return EvaluationSummaryResponse(
        start_date=config.start_date,
        end_date=config.end_date,
        day_ahead_cutoff_time=cutoff_str,
        alignment=config.alignment,
        total_target_intervals=result.audit.total_target_intervals,
        matched_intervals=result.audit.matched_intervals,
        coverage_rate_percent=result.audit.coverage_rate_percent,
        mae_mw=m.mae_mw if m else None,
        rmse_mw=m.rmse_mw if m else None,
        signed_bias_mw=m.signed_bias_mw if m else None,
        mape_percent=m.mape_percent if m else None,
        wmape_percent=m.wmape_percent if m else None,
        total_forecast_energy_mwh=m.total_forecast_energy_mwh if m else None,
        total_actual_energy_mwh=m.total_actual_energy_mwh if m else None,
        mape_valid_samples=m.mape_valid_samples if m else 0,
        mape_excluded_zero_samples=m.mape_excluded_zero_samples if m else 0,
    )


@router.get(
    "/timeseries",
    response_model=TimeSeriesResponse,
    summary="Chronological Matched Time-Series Observations",
    description="Returns timestamped forecast and actual generation pairs formatted for time-series charts.",
)
def get_evaluation_timeseries(params: Tuple[EvaluationConfig, bool] = Depends(parse_and_validate_params)):
    config, use_cache = params
    result = run_evaluation_pipeline(config, use_cache)

    return TimeSeriesResponse(
        alignment=config.alignment,
        total_observations=len(result.observations),
        series=result.observations,
    )


@router.get(
    "/exclusions",
    response_model=ExclusionsResponse,
    summary="Audit Log & Exclusions Breakdown",
    description="Returns audit breakdown of missing forecasts, missing actuals, post-cutoff exclusions, and hindcast discards.",
)
def get_evaluation_exclusions(params: Tuple[EvaluationConfig, bool] = Depends(parse_and_validate_params)):
    config, use_cache = params
    result = run_evaluation_pipeline(config, use_cache)
    a = result.audit

    return ExclusionsResponse(
        total_target_intervals=a.total_target_intervals,
        matched_intervals=a.matched_intervals,
        coverage_rate_percent=a.coverage_rate_percent,
        missing_actual_count=a.missing_actual_count,
        missing_forecast_count=a.missing_forecast_count,
        excluded_non_target_delivery_records=a.excluded_non_target_delivery_records,
        excluded_retrospective_forecasts=a.excluded_retrospective_forecasts,
        excluded_post_cutoff_forecasts=a.excluded_post_cutoff_forecasts,
        unmatched_intervals=a.unmatched_intervals,
        ingestion_audit_actuals=a.ingestion_audit_actuals,
        ingestion_audit_forecasts=a.ingestion_audit_forecasts,
    )
