import math
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from backend.app.schemas.analysis import (
    AccuracyMetrics,
    EvaluationAudit,
    EvaluationConfig,
    EvaluationResult,
    IntervalExclusion,
    MatchedObservation,
    ResolutionAlignment,
)
from backend.app.schemas.elexon import (
    FuelHHRecord,
    IngestionAudit,
    WindforRecord,
)


class ForecastEvaluator:
    """
    Engine for reconstructing day-ahead wind generation forecasts and quantitatively
    evaluating their accuracy against FUELHH outturn records.
    """

    @staticmethod
    def _generate_target_intervals(
        start_date: date,
        end_date: date,
        alignment: ResolutionAlignment,
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generate continuous, gap-free target intervals for the delivery period in UTC.
        """
        intervals: List[Tuple[datetime, datetime]] = []
        step = timedelta(hours=1) if alignment == ResolutionAlignment.HOURLY else timedelta(minutes=30)

        current_dt = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)

        while current_dt < end_dt:
            interval_end = current_dt + step
            intervals.append((current_dt, interval_end))
            current_dt = interval_end

        return intervals

    @staticmethod
    def _process_actuals(
        fuelhh_records: List[FuelHHRecord],
        target_intervals: List[Tuple[datetime, datetime]],
        alignment: ResolutionAlignment,
        eval_start_dt: datetime,
        eval_end_dt: datetime,
    ) -> Tuple[Dict[datetime, float], int]:
        """
        Map FUELHH records to target delivery intervals.
        - HOURLY: Average SP 2k-1 and SP 2k. If either is missing, the hour is missing.
        - HALF_HOURLY: Direct 1-to-1 mapping.
        Returns:
            dict of {interval_start: actual_generation_mw},
            count of excluded non-target delivery records.
        """
        excluded_non_target = 0
        actuals_by_start: Dict[datetime, float] = {}

        # Index valid half-hourly outturn by startTime
        hh_map: Dict[datetime, float] = {}
        for r in fuelhh_records:
            # Check delivery bounds
            if r.start_time < eval_start_dt or r.start_time >= eval_end_dt:
                excluded_non_target += 1
                continue
            hh_map[r.start_time] = r.generation

        if alignment == ResolutionAlignment.HALF_HOURLY:
            for start_t, _ in target_intervals:
                if start_t in hh_map:
                    actuals_by_start[start_t] = hh_map[start_t]
        else:
            # HOURLY: Require both half-hour periods (HH:00 and HH:30)
            for start_t, _ in target_intervals:
                hh1 = hh_map.get(start_t)
                hh2 = hh_map.get(start_t + timedelta(minutes=30))
                if hh1 is not None and hh2 is not None:
                    # Physically exact arithmetic average of power over the hour
                    actuals_by_start[start_t] = (hh1 + hh2) / 2.0

        return actuals_by_start, excluded_non_target

    @staticmethod
    def _select_day_ahead_forecasts(
        windfor_records: List[WindforRecord],
        target_intervals: List[Tuple[datetime, datetime]],
        config: EvaluationConfig,
        eval_start_dt: datetime,
        eval_end_dt: datetime,
    ) -> Tuple[Dict[datetime, Tuple[float, datetime]], int, int, int]:
        """
        Select the latest forecast published on or before the day-ahead decision cutoff.
        Enforces:
        - publishTime <= Cutoff(D)
        - publishTime < delivery startTime (Strict forward-looking causality)
        - Retrospective records (startTime <= publishTime) are excluded.
        Returns:
            dict of {interval_start: (forecast_generation_mw, publish_time)},
            count of excluded non-target delivery records,
            count of excluded retrospective forecasts,
            count of excluded post-cutoff forecasts.
        """
        excluded_non_target = 0
        excluded_retrospective = 0
        excluded_post_cutoff = 0

        # Group candidate forecasts by target delivery hour: delivery_start -> list[WindforRecord]
        candidates_by_hour: Dict[datetime, List[WindforRecord]] = {}

        for r in windfor_records:
            # 1. Delivery window check: exclude delivery intervals outside evaluation range
            if r.start_time < eval_start_dt or r.start_time >= eval_end_dt:
                excluded_non_target += 1
                continue

            # 2. Causality check: exclude retrospective hindcasts
            if r.start_time <= r.publish_time:
                excluded_retrospective += 1
                continue

            # 3. Decision Cutoff check:
            # Delivery date D in UTC
            delivery_date = r.start_time.date()
            cutoff_dt = datetime.combine(
                delivery_date - timedelta(days=1),
                config.day_ahead_cutoff_time,
                tzinfo=timezone.utc,
            )

            # Must have been published on or before the cutoff timestamp
            if r.publish_time > cutoff_dt:
                excluded_post_cutoff += 1
                continue

            candidates_by_hour.setdefault(r.start_time, []).append(r)

        # For each target interval, select latest publication
        selected_forecasts: Dict[datetime, Tuple[float, datetime]] = {}

        for start_t, _ in target_intervals:
            # For hourly, start_t is top of the hour.
            # For half-hourly, the hourly forecast applies to both half-hours of that hour.
            hourly_start = start_t.replace(minute=0, second=0, microsecond=0)
            candidates = candidates_by_hour.get(hourly_start, [])
            if candidates:
                # Select latest publication before cutoff
                best = max(candidates, key=lambda c: c.publish_time)
                selected_forecasts[start_t] = (best.generation, best.publish_time)

        return (
            selected_forecasts,
            excluded_non_target,
            excluded_retrospective,
            excluded_post_cutoff,
        )

    @classmethod
    def evaluate(
        cls,
        fuelhh_records: List[FuelHHRecord],
        windfor_records: List[WindforRecord],
        config: Optional[EvaluationConfig] = None,
        ingestion_audit_actuals: Optional[IngestionAudit] = None,
        ingestion_audit_forecasts: Optional[IngestionAudit] = None,
    ) -> EvaluationResult:
        """
        Execute full forecast evaluation pipeline:
        1. Generate continuous delivery intervals.
        2. Map actual outturn.
        3. Select day-ahead forecasts under cutoff policy.
        4. Match intervals and audit exclusions.
        5. Compute MAE, RMSE, Signed Bias, MAPE, and WMAPE.
        """
        if config is None:
            config = EvaluationConfig()

        eval_start_dt = datetime.combine(config.start_date, dt_time.min, tzinfo=timezone.utc)
        eval_end_dt = datetime.combine(config.end_date + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)

        target_intervals = cls._generate_target_intervals(
            config.start_date, config.end_date, config.alignment
        )
        total_target = len(target_intervals)

        # 1. Process actuals
        actuals_by_start, excl_actuals_non_target = cls._process_actuals(
            fuelhh_records, target_intervals, config.alignment, eval_start_dt, eval_end_dt
        )

        # 2. Select forecasts
        (
            forecasts_by_start,
            excl_forecasts_non_target,
            excl_retrospective,
            excl_post_cutoff,
        ) = cls._select_day_ahead_forecasts(
            windfor_records, target_intervals, config, eval_start_dt, eval_end_dt
        )

        # 3. Match observations
        observations: List[MatchedObservation] = []
        unmatched_intervals: List[IntervalExclusion] = []
        missing_actual_count = 0
        missing_forecast_count = 0

        interval_hours = 1.0 if config.alignment == ResolutionAlignment.HOURLY else 0.5

        for start_t, end_t in target_intervals:
            has_actual = start_t in actuals_by_start
            has_forecast = start_t in forecasts_by_start

            if has_actual and has_forecast:
                act = actuals_by_start[start_t]
                fc, pub_t = forecasts_by_start[start_t]
                err = fc - act
                abs_err = abs(err)
                pct_err = (abs_err / act * 100.0) if act >= config.mape_epsilon else None

                observations.append(
                    MatchedObservation(
                        interval_start=start_t,
                        interval_end=end_t,
                        forecast_mw=fc,
                        actual_mw=act,
                        forecast_publish_time=pub_t,
                        error_mw=err,
                        absolute_error_mw=abs_err,
                        percentage_error=pct_err,
                    )
                )
            else:
                if not has_actual and not has_forecast:
                    missing_actual_count += 1
                    missing_forecast_count += 1
                    unmatched_intervals.append(
                        IntervalExclusion(interval_start=start_t, reason="MISSING_BOTH")
                    )
                elif not has_actual:
                    missing_actual_count += 1
                    unmatched_intervals.append(
                        IntervalExclusion(interval_start=start_t, reason="MISSING_ACTUAL")
                    )
                else:
                    missing_forecast_count += 1
                    unmatched_intervals.append(
                        IntervalExclusion(interval_start=start_t, reason="MISSING_FORECAST")
                    )

        matched_count = len(observations)
        coverage_rate = (matched_count / total_target * 100.0) if total_target > 0 else 0.0

        audit = EvaluationAudit(
            total_target_intervals=total_target,
            matched_intervals=matched_count,
            coverage_rate_percent=round(coverage_rate, 4),
            missing_actual_count=missing_actual_count,
            missing_forecast_count=missing_forecast_count,
            excluded_non_target_delivery_records=excl_actuals_non_target + excl_forecasts_non_target,
            excluded_retrospective_forecasts=excl_retrospective,
            excluded_post_cutoff_forecasts=excl_post_cutoff,
            unmatched_intervals=unmatched_intervals,
            ingestion_audit_actuals=ingestion_audit_actuals,
            ingestion_audit_forecasts=ingestion_audit_forecasts,
        )

        # 4. Compute Metrics
        metrics = None
        if matched_count > 0:
            sum_abs_err = sum(obs.absolute_error_mw for obs in observations)
            sum_sq_err = sum(obs.error_mw ** 2 for obs in observations)
            sum_signed_err = sum(obs.error_mw for obs in observations)
            sum_actual = sum(obs.actual_mw for obs in observations)
            sum_forecast = sum(obs.forecast_mw for obs in observations)

            mae = sum_abs_err / matched_count
            rmse = math.sqrt(sum_sq_err / matched_count)
            signed_bias = sum_signed_err / matched_count

            # MAPE with explicit epsilon filtering
            mape_samples = [obs.percentage_error for obs in observations if obs.percentage_error is not None]
            mape_val = (sum(mape_samples) / len(mape_samples)) if mape_samples else None
            mape_excluded = matched_count - len(mape_samples)

            # WMAPE: sum(|F - A|) / sum(A) * 100%
            wmape_val = (sum_abs_err / sum_actual * 100.0) if sum_actual > 0 else None

            metrics = AccuracyMetrics(
                sample_size=matched_count,
                mae_mw=round(mae, 4),
                rmse_mw=round(rmse, 4),
                signed_bias_mw=round(signed_bias, 4),
                mape_percent=round(mape_val, 4) if mape_val is not None else None,
                wmape_percent=round(wmape_val, 4) if wmape_val is not None else None,
                total_forecast_energy_mwh=round(sum_forecast * interval_hours, 2),
                total_actual_energy_mwh=round(sum_actual * interval_hours, 2),
                mape_valid_samples=len(mape_samples),
                mape_excluded_zero_samples=mape_excluded,
            )

        return EvaluationResult(
            config=config,
            metrics=metrics,
            audit=audit,
            observations=observations,
        )
