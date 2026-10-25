import math
from datetime import date, datetime, time, timedelta, timezone

import pytest

from backend.app.schemas.analysis import (
    AccuracyMetrics,
    EvaluationConfig,
    ResolutionAlignment,
)
from backend.app.schemas.elexon import FuelHHRecord, WindforRecord
from backend.app.services.forecast_evaluator import ForecastEvaluator


def make_fuelhh(dt_str: str, sp: int, gen: float) -> FuelHHRecord:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return FuelHHRecord(
        dataset="FUELHH",
        publishTime=dt + timedelta(minutes=30),
        startTime=dt,
        settlementDate=dt.strftime("%Y-%m-%d"),
        settlementPeriod=sp,
        fuelType="WIND",
        generation=gen,
    )


def make_windfor(pub_str: str, start_str: str, gen: float) -> WindforRecord:
    pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    return WindforRecord(
        dataset="WINDFOR",
        publishTime=pub,
        startTime=start,
        generation=gen,
    )


# =====================================================================
# 1. Day-Ahead Decision Cutoff & Forward-Looking Causality Tests
# =====================================================================


def test_forecast_published_strictly_before_cutoff_is_eligible():
    # Delivery on 2026-01-02 10:00:00Z -> Cutoff is 2026-01-01 17:00:00Z
    # Published at 2026-01-01 16:30:00Z (before cutoff) -> Eligible
    fc = make_windfor("2026-01-01T16:30:00Z", "2026-01-02T10:00:00Z", 1500.0)
    act1 = make_fuelhh("2026-01-02T10:00:00Z", 21, 1400.0)
    act2 = make_fuelhh("2026-01-02T10:30:00Z", 22, 1600.0)

    config = EvaluationConfig(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 1
    obs = res.observations[0]
    assert obs.forecast_mw == 1500.0
    assert obs.actual_mw == 1500.0  # (1400 + 1600) / 2
    assert obs.forecast_publish_time == datetime(2026, 1, 1, 16, 30, tzinfo=timezone.utc)


def test_forecast_published_exactly_at_cutoff_is_eligible():
    # Published at exactly 17:00:00Z on D-1 -> Eligible (inclusive cutoff)
    fc = make_windfor("2026-01-01T17:00:00Z", "2026-01-02T10:00:00Z", 2000.0)
    act1 = make_fuelhh("2026-01-02T10:00:00Z", 21, 1900.0)
    act2 = make_fuelhh("2026-01-02T10:30:00Z", 22, 2100.0)

    config = EvaluationConfig(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 1
    assert res.observations[0].forecast_mw == 2000.0


def test_forecast_published_after_cutoff_is_excluded():
    # Published at 17:00:01Z on D-1 (1 second after cutoff) -> Excluded
    fc = make_windfor("2026-01-01T17:00:01Z", "2026-01-02T10:00:00Z", 2500.0)
    act1 = make_fuelhh("2026-01-02T10:00:00Z", 21, 2000.0)
    act2 = make_fuelhh("2026-01-02T10:30:00Z", 22, 2000.0)

    config = EvaluationConfig(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 0
    assert res.audit.excluded_post_cutoff_forecasts == 1
    target_dt = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    exclusions = {ex.interval_start: ex.reason for ex in res.audit.unmatched_intervals}
    assert exclusions[target_dt] == "MISSING_FORECAST"


def test_retrospective_forecast_is_excluded():
    # Delivery startTime (04:00) <= publishTime (04:30) -> Retrospective hindcast
    fc = make_windfor("2026-01-02T04:30:00Z", "2026-01-02T04:00:00Z", 3000.0)
    act1 = make_fuelhh("2026-01-02T04:00:00Z", 9, 3000.0)
    act2 = make_fuelhh("2026-01-02T04:30:00Z", 10, 3000.0)

    config = EvaluationConfig(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 0
    assert res.audit.excluded_retrospective_forecasts == 1


def test_multiple_eligible_forecasts_selects_latest():
    # Two forecasts published before cutoff: 09:30 and 15:30
    fc_early = make_windfor("2026-01-01T09:30:00Z", "2026-01-02T12:00:00Z", 1100.0)
    fc_latest = make_windfor("2026-01-01T15:30:00Z", "2026-01-02T12:00:00Z", 1350.0)
    act1 = make_fuelhh("2026-01-02T12:00:00Z", 25, 1300.0)
    act2 = make_fuelhh("2026-01-02T12:30:00Z", 26, 1400.0)

    config = EvaluationConfig(start_date=date(2026, 1, 2), end_date=date(2026, 1, 2))
    res = ForecastEvaluator.evaluate([act1, act2], [fc_early, fc_latest], config)

    assert len(res.observations) == 1
    assert res.observations[0].forecast_mw == 1350.0
    assert res.observations[0].forecast_publish_time == datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc)


# =====================================================================
# 2. Date Boundary & December Isolation Tests
# =====================================================================


def test_december_publication_used_for_january_1_delivery():
    # Published on 2025-12-31 at 15:30 for delivery 2026-01-01 00:00:00Z
    fc = make_windfor("2025-12-31T15:30:00Z", "2026-01-01T00:00:00Z", 5000.0)
    act1 = make_fuelhh("2026-01-01T00:00:00Z", 1, 4800.0)
    act2 = make_fuelhh("2026-01-01T00:30:00Z", 2, 5200.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 1
    assert res.observations[0].forecast_mw == 5000.0
    assert res.observations[0].actual_mw == 5000.0


def test_december_delivery_intervals_strictly_excluded_from_january_metrics():
    # Delivery on 2025-12-31 23:00:00Z -> Outside evaluation window
    fc_dec = make_windfor("2025-12-30T15:30:00Z", "2025-12-31T23:00:00Z", 4000.0)
    act_dec = make_fuelhh("2025-12-31T23:00:00Z", 47, 4000.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    res = ForecastEvaluator.evaluate([act_dec], [fc_dec], config)

    assert len(res.observations) == 0
    assert res.audit.excluded_non_target_delivery_records == 2


# =====================================================================
# 3. Interval Alignment Tests (Hourly vs Half-Hourly)
# =====================================================================


def test_hourly_aggregation_requires_both_settlement_periods():
    # SP 1 exists, SP 2 is missing
    act1 = make_fuelhh("2026-01-01T00:00:00Z", 1, 3000.0)
    fc = make_windfor("2025-12-31T15:30:00Z", "2026-01-01T00:00:00Z", 3000.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1), alignment=ResolutionAlignment.HOURLY)
    res = ForecastEvaluator.evaluate([act1], [fc], config)

    # Missing SP 2 means the hour cannot be formed (no fabricated data!)
    assert len(res.observations) == 0
    target_dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    exclusions = {ex.interval_start: ex.reason for ex in res.audit.unmatched_intervals}
    assert exclusions[target_dt] == "MISSING_ACTUAL"


def test_half_hourly_broadcasting():
    # 1-hour forecast applies to both SP 1 (00:00) and SP 2 (00:30)
    fc = make_windfor("2025-12-31T15:30:00Z", "2026-01-01T00:00:00Z", 4000.0)
    act1 = make_fuelhh("2026-01-01T00:00:00Z", 1, 3800.0)
    act2 = make_fuelhh("2026-01-01T00:30:00Z", 2, 4200.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1), alignment=ResolutionAlignment.HALF_HOURLY)
    res = ForecastEvaluator.evaluate([act1, act2], [fc], config)

    assert len(res.observations) == 2
    assert res.observations[0].forecast_mw == 4000.0
    assert res.observations[0].actual_mw == 3800.0
    assert res.observations[1].forecast_mw == 4000.0
    assert res.observations[1].actual_mw == 4200.0


# =====================================================================
# 4. Metric Formulas & Zero Handling Tests
# =====================================================================


def test_accuracy_metrics_hand_calculated_verification():
    """
    Known synthetic dataset:
    Obs 1: Forecast = 110, Actual = 100 -> error = +10, abs = 10, pct = 10.0%
    Obs 2: Forecast = 180, Actual = 200 -> error = -20, abs = 20, pct = 10.0%
    Obs 3: Forecast = 310, Actual = 300 -> error = +10, abs = 10, pct = 3.3333%
    Obs 4: Forecast = 400, Actual = 400 -> error = 0,   abs = 0,  pct = 0.0%

    Expected Hand Calculations:
    MAE: (10 + 20 + 10 + 0) / 4 = 10.0 MW
    RMSE: sqrt((100 + 400 + 100 + 0) / 4) = sqrt(600 / 4) = sqrt(150) = 12.2474 MW
    Signed Bias: (10 - 20 + 10 + 0) / 4 = 0.0 MW
    MAPE: (10 + 10 + 3.333333 + 0) / 4 = 5.8333%
    WMAPE: sum(abs) / sum(actual) * 100 = 40 / 1000 * 100 = 4.0%
    """
    start_d = date(2026, 1, 1)
    acts = []
    fcs = []
    pairs = [(110.0, 100.0), (180.0, 200.0), (310.0, 300.0), (400.0, 400.0)]

    for i, (f_val, a_val) in enumerate(pairs):
        t_str = f"2026-01-01T{i:02d}:00:00Z"
        t_str_half = f"2026-01-01T{i:02d}:30:00Z"
        fcs.append(make_windfor("2025-12-31T15:00:00Z", t_str, f_val))
        acts.append(make_fuelhh(t_str, i * 2 + 1, a_val))
        acts.append(make_fuelhh(t_str_half, i * 2 + 2, a_val))

    config = EvaluationConfig(start_date=start_d, end_date=start_d)
    res = ForecastEvaluator.evaluate(acts, fcs, config)

    m = res.metrics
    assert m is not None
    assert m.sample_size == 4
    assert m.mae_mw == 10.0
    assert m.rmse_mw == 12.2474
    assert m.signed_bias_mw == 0.0
    assert m.mape_percent == 5.8333
    assert m.wmape_percent == 4.0
    assert m.mape_valid_samples == 4
    assert m.mape_excluded_zero_samples == 0


def test_zero_actual_handling_in_mape_and_wmape():
    # Obs 1: Forecast = 50, Actual = 0.0 MW (< epsilon: excluded from MAPE)
    # Obs 2: Forecast = 120, Actual = 100.0 MW (included in MAPE: 20%)
    fc1 = make_windfor("2025-12-31T15:00:00Z", "2026-01-01T00:00:00Z", 50.0)
    fc2 = make_windfor("2025-12-31T15:00:00Z", "2026-01-01T01:00:00Z", 120.0)

    act1_a = make_fuelhh("2026-01-01T00:00:00Z", 1, 0.0)
    act1_b = make_fuelhh("2026-01-01T00:30:00Z", 2, 0.0)
    act2_a = make_fuelhh("2026-01-01T01:00:00Z", 3, 100.0)
    act2_b = make_fuelhh("2026-01-01T01:30:00Z", 4, 100.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1), mape_epsilon=1.0)
    res = ForecastEvaluator.evaluate([act1_a, act1_b, act2_a, act2_b], [fc1, fc2], config)

    m = res.metrics
    assert m is not None
    assert m.sample_size == 2
    # MAE includes both: (50 + 20) / 2 = 35.0
    assert m.mae_mw == 35.0
    # MAPE only evaluated on Obs 2 (20.0%)
    assert m.mape_percent == 20.0
    assert m.mape_valid_samples == 1
    assert m.mape_excluded_zero_samples == 1
    # WMAPE: (50 + 20) / (0 + 100) * 100 = 70.0%
    assert m.wmape_percent == 70.0


def test_zero_total_actual_wmape_returns_none():
    # Both actuals are 0.0 MW
    fc1 = make_windfor("2025-12-31T15:00:00Z", "2026-01-01T00:00:00Z", 50.0)
    act1_a = make_fuelhh("2026-01-01T00:00:00Z", 1, 0.0)
    act1_b = make_fuelhh("2026-01-01T00:30:00Z", 2, 0.0)

    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    res = ForecastEvaluator.evaluate([act1_a, act1_b], [fc1], config)

    m = res.metrics
    assert m is not None
    assert m.mape_percent is None
    assert m.wmape_percent is None
    assert m.mape_excluded_zero_samples == 1


def test_zero_matched_observations_returns_none_metrics():
    config = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    res = ForecastEvaluator.evaluate([], [], config)

    assert res.metrics is None
    assert res.audit.matched_intervals == 0
    assert res.audit.coverage_rate_percent == 0.0
    assert res.audit.total_target_intervals == 24


def test_full_january_target_intervals_count():
    config_hourly = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), alignment=ResolutionAlignment.HOURLY)
    res_hourly = ForecastEvaluator.evaluate([], [], config_hourly)
    assert res_hourly.audit.total_target_intervals == 31 * 24  # 744 intervals

    config_half = EvaluationConfig(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), alignment=ResolutionAlignment.HALF_HOURLY)
    res_half = ForecastEvaluator.evaluate([], [], config_half)
    assert res_half.audit.total_target_intervals == 31 * 48  # 1488 intervals
