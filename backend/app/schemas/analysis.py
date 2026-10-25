from datetime import date, datetime, time
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.elexon import IngestionAudit


class ResolutionAlignment(str, Enum):
    """
    Temporal resolution alignment method between FUELHH (30-min) and WINDFOR (60-min).
    - HOURLY: Averages the two half-hourly actuals to match the 1-hour forecast (Physically exact, default).
    - HALF_HOURLY: Broadcasts the 1-hour forecast to each constituent 30-min settlement period.
    """
    HOURLY = "HOURLY"
    HALF_HOURLY = "HALF_HOURLY"


class EvaluationConfig(BaseModel):
    """
    Configuration for forecast reconstruction and quantitative evaluation.
    
    Assumption Disclosure:
    - day_ahead_cutoff_time defaults to 17:00:00 UTC on day D-1. This is a pilot assumption
      aligned with the NGESO Day-Ahead Indicative Operational Plan submission deadline,
      rather than an official statutory gate closure.
    """
    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(default=date(2026, 1, 1), description="Evaluation start date inclusive")
    end_date: date = Field(default=date(2026, 1, 31), description="Evaluation end date inclusive")
    day_ahead_cutoff_time: time = Field(
        default=time(17, 0, 0),
        description="Day-ahead cutoff time in UTC on day D-1 (pilot assumption: 17:00 UTC)",
    )
    alignment: ResolutionAlignment = Field(
        default=ResolutionAlignment.HOURLY,
        description="Temporal resolution alignment method",
    )
    mape_epsilon: float = Field(
        default=1.0,
        ge=0.0,
        description="Threshold in MW below which actual generation is excluded from MAPE to avoid division by zero",
    )


class MatchedObservation(BaseModel):
    """A matched delivery interval with paired day-ahead forecast and actual outturn."""
    interval_start: datetime
    interval_end: datetime
    forecast_mw: float
    actual_mw: float
    forecast_publish_time: datetime
    error_mw: float = Field(description="Signed forecast error: Forecast - Actual")
    absolute_error_mw: float = Field(description="Absolute error: |Forecast - Actual|")
    percentage_error: Optional[float] = Field(
        default=None,
        description="Absolute percentage error (|Forecast - Actual| / Actual * 100). None if Actual < mape_epsilon.",
    )


class AccuracyMetrics(BaseModel):
    """Quantitative forecast accuracy evaluation metrics."""
    sample_size: int = Field(description="Number of valid matched observations evaluated")
    mae_mw: float = Field(description="Mean Absolute Error in MW")
    rmse_mw: float = Field(description="Root Mean Square Error in MW")
    signed_bias_mw: float = Field(description="Mean Forecast Error in MW: mean(Forecast - Actual)")
    mape_percent: Optional[float] = Field(
        default=None,
        description="Mean Absolute Percentage Error (%). None if all actuals are below epsilon.",
    )
    wmape_percent: Optional[float] = Field(
        default=None,
        description="Weighted MAPE / Normalized MAE: sum(|Forecast - Actual|) / sum(Actual) * 100. None if sum(Actual) == 0.",
    )
    total_forecast_energy_mwh: float = Field(description="Total forecasted energy volume over matched intervals in MWh")
    total_actual_energy_mwh: float = Field(description="Total actual energy outturn over matched intervals in MWh")
    mape_valid_samples: int = Field(description="Number of samples included in MAPE calculation")
    mape_excluded_zero_samples: int = Field(description="Number of samples where Actual < epsilon (excluded from MAPE)")


class IntervalExclusion(BaseModel):
    """Audit record for an unmatched target delivery interval."""
    interval_start: datetime
    reason: str  # "MISSING_ACTUAL", "MISSING_FORECAST", "DECEMBER_DELIVERY_INTERVAL"


class EvaluationAudit(BaseModel):
    """Audit report for the evaluation process."""
    total_target_intervals: int
    matched_intervals: int
    coverage_rate_percent: float
    missing_actual_count: int
    missing_forecast_count: int
    excluded_non_target_delivery_records: int
    excluded_retrospective_forecasts: int = Field(description="Forecasts where startTime <= publishTime (hindcasts)")
    excluded_post_cutoff_forecasts: int = Field(description="Forecasts published after the day-ahead decision cutoff")
    unmatched_intervals: List[IntervalExclusion] = Field(default_factory=list)
    ingestion_audit_actuals: Optional[IngestionAudit] = None
    ingestion_audit_forecasts: Optional[IngestionAudit] = None


class EvaluationResult(BaseModel):
    """Complete evaluation outcome containing configuration, metrics, audit, and time-series observations."""
    config: EvaluationConfig
    metrics: Optional[AccuracyMetrics]
    audit: EvaluationAudit
    observations: List[MatchedObservation] = Field(default_factory=list)
