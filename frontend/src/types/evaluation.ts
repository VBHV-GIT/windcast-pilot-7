export type ResolutionAlignment = "HOURLY" | "HALF_HOURLY";

export interface EvaluationQueryParams {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  cutoffTime: string; // HH:MM or HH:MM:SS
  alignment: ResolutionAlignment;
  useCache: boolean;
}

export interface EvaluationSummaryResponse {
  start_date: string;
  end_date: string;
  day_ahead_cutoff_time: string;
  alignment: ResolutionAlignment;
  total_target_intervals: number;
  matched_intervals: number;
  coverage_rate_percent: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  signed_bias_mw: number | null;
  mape_percent: number | null;
  wmape_percent: number | null;
  total_forecast_energy_mwh: number | null;
  total_actual_energy_mwh: number | null;
  mape_valid_samples: number;
  mape_excluded_zero_samples: number;
}

export interface MatchedObservation {
  interval_start: string;
  interval_end: string;
  forecast_mw: number;
  actual_mw: number;
  forecast_publish_time: string;
  error_mw: number;
  absolute_error_mw: number;
  percentage_error: number | null;
}

export interface TimeSeriesResponse {
  alignment: ResolutionAlignment;
  total_observations: number;
  series: MatchedObservation[];
}

export interface IntervalExclusion {
  interval_start: string;
  reason: string; // "MISSING_ACTUAL", "MISSING_FORECAST", "MISSING_BOTH"
}

export interface IngestionAudit {
  dataset: string;
  chunks_requested: number;
  raw_records_received: number;
  records_retained: number;
  duplicate_records_excluded: number;
  non_wind_records_excluded: number;
  malformed_records_excluded: number;
  exclusion_notes: string[];
}

export interface ExclusionsResponse {
  total_target_intervals: number;
  matched_intervals: number;
  coverage_rate_percent: number;
  missing_actual_count: number;
  missing_forecast_count: number;
  excluded_non_target_delivery_records: number;
  excluded_retrospective_forecasts: number;
  excluded_post_cutoff_forecasts: number;
  unmatched_intervals: IntervalExclusion[];
  ingestion_audit_actuals?: IngestionAudit | null;
  ingestion_audit_forecasts?: IngestionAudit | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}
