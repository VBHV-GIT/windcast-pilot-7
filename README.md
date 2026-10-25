# WindCast Analytics

A full-stack web application designed for UK electricity procurement teams to evaluate wind generation forecasts against outturn actuals from the Elexon BMRS Insights Solution for January 2026.

---

## 1. Project Structure

```text
windcast-analysis/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application entrypoint & routing
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── evaluation.py           # REST endpoints: /evaluation, /summary, /timeseries, /exclusions
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── elexon.py               # FUELHH and WINDFOR Pydantic models & audit logs
│   │   │   └── analysis.py             # Evaluation models, metrics, and configs
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── elexon_client.py        # Elexon BMRS client, chunking, retries, deduplication
│   │       └── forecast_evaluator.py   # Forecast reconstruction, cutoff filtering & accuracy metrics
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py              # Health check tests
│   │   ├── test_elexon_client.py       # Chunking, validation, retries & deduplication tests
│   │   ├── test_elexon_smoke.py        # Isolated live API smoke tests (RUN_LIVE_TESTS=1)
│   │   ├── test_forecast_evaluator.py  # Forecast selection, cutoffs, alignment & metric formula tests
│   │   └── test_api.py                 # FastAPI route tests, parameter validation & error handling
│   ├── pytest.ini                      # Pytest marker registration
│   └── requirements.txt                # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx                     # Presentation component
│   │   ├── main.tsx                    # React entrypoint
│   │   └── index.css                   # Tailwind CSS directives
│   ├── package.json                    # Node dependencies
│   ├── tsconfig.json                   # TypeScript configuration
│   ├── vite.config.ts                  # Vite build & proxy configuration
│   └── tailwind.config.js              # Tailwind CSS theme configuration
├── .gitignore                          # Version control ignore rules
└── README.md                           # Documentation & API specifications
```

---

## 2. API Endpoints Specification

All endpoints are served under `/api` and support interactive documentation at `/docs` (Swagger UI) and `/redoc`.

### Query Parameters (Common Across Evaluation Endpoints)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `YYYY-MM-DD` | `2026-01-01` | Delivery start date inclusive. |
| `end_date` | `YYYY-MM-DD` | `2026-01-31` | Delivery end date inclusive (max 35-day span). |
| `cutoff_time` | `HH:MM` or `HH:MM:SS` | `17:00` | Day-ahead cutoff on day $D-1$ in UTC (**Pilot Assumption: 17:00 UTC**). |
| `alignment` | `string` | `HOURLY` | Resolution alignment: `HOURLY` (physically exact average) or `HALF_HOURLY` (broadcast). |
| `use_cache` | `boolean` | `false` | Whether to use cached raw Elexon API responses. |

---

### `GET /api/evaluation`
Reconstructs day-ahead forecasts under the specified cutoff, matches them with actual outturn, and returns the complete evaluation dataset including metrics, audit, and matched observations.

**Example Request**:
```http
GET /api/evaluation?start_date=2026-01-01&end_date=2026-01-01&cutoff_time=17:00&alignment=HOURLY
```

**Example Response**:
```json
{
  "config": {
    "start_date": "2026-01-01",
    "end_date": "2026-01-01",
    "day_ahead_cutoff_time": "17:00:00",
    "alignment": "HOURLY",
    "mape_epsilon": 1.0
  },
  "metrics": {
    "sample_size": 24,
    "mae_mw": 4217.4167,
    "rmse_mw": 4277.9223,
    "signed_bias_mw": 4217.4167,
    "mape_percent": 27.6507,
    "wmape_percent": 27.4358,
    "total_forecast_energy_mwh": 470145.0,
    "total_actual_energy_mwh": 368927.0,
    "mape_valid_samples": 24,
    "mape_excluded_zero_samples": 0
  },
  "audit": {
    "total_target_intervals": 24,
    "matched_intervals": 24,
    "coverage_rate_percent": 100.0,
    "missing_actual_count": 0,
    "missing_forecast_count": 0,
    "excluded_non_target_delivery_records": 0,
    "excluded_retrospective_forecasts": 0,
    "excluded_post_cutoff_forecasts": 0,
    "unmatched_intervals": []
  },
  "observations": [
    {
      "interval_start": "2026-01-01T00:00:00Z",
      "interval_end": "2026-01-01T01:00:00Z",
      "forecast_mw": 19595.0,
      "actual_mw": 13814.5,
      "forecast_publish_time": "2025-12-31T15:30:00Z",
      "error_mw": 5780.5,
      "absolute_error_mw": 5780.5,
      "percentage_error": 41.8437
    }
  ]
}
```

---

### `GET /api/evaluation/summary`
Returns high-level Key Performance Indicators (KPIs) formatted for executive cards and summary widgets. Unavailable metrics are returned as `null` (not zero).

**Example Response**:
```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-01-01",
  "day_ahead_cutoff_time": "17:00",
  "alignment": "HOURLY",
  "total_target_intervals": 24,
  "matched_intervals": 24,
  "coverage_rate_percent": 100.0,
  "mae_mw": 4217.4167,
  "rmse_mw": 4277.9223,
  "signed_bias_mw": 4217.4167,
  "mape_percent": 27.6507,
  "wmape_percent": 27.4358,
  "total_forecast_energy_mwh": 470145.0,
  "total_actual_energy_mwh": 368927.0,
  "mape_valid_samples": 24,
  "mape_excluded_zero_samples": 0
}
```

---

### `GET /api/evaluation/timeseries`
Returns chronological observations formatted specifically for charting libraries (Recharts / Chart.js).

**Example Response**:
```json
{
  "alignment": "HOURLY",
  "total_observations": 24,
  "series": [
    {
      "interval_start": "2026-01-01T00:00:00Z",
      "interval_end": "2026-01-01T01:00:00Z",
      "forecast_mw": 19595.0,
      "actual_mw": 13814.5,
      "forecast_publish_time": "2025-12-31T15:30:00Z",
      "error_mw": 5780.5,
      "absolute_error_mw": 5780.5,
      "percentage_error": 41.8437
    }
  ]
}
```

---

### `GET /api/evaluation/exclusions`
Returns a transparent audit breakdown of matched vs missing intervals, retrospective hindcast discards, and post-cutoff exclusions.

**Example Response**:
```json
{
  "total_target_intervals": 24,
  "matched_intervals": 24,
  "coverage_rate_percent": 100.0,
  "missing_actual_count": 0,
  "missing_forecast_count": 0,
  "excluded_non_target_delivery_records": 0,
  "excluded_retrospective_forecasts": 0,
  "excluded_post_cutoff_forecasts": 0,
  "unmatched_intervals": []
}
```

---

### Error Handling & HTTP Status Codes

- **`400 Bad Request`**:
  - `start_date` occurs after `end_date`.
  - Date span exceeds 35 days.
  - Invalid `cutoff_time` format (e.g. `25:00`).
- **`422 Unprocessable Entity`**:
  - Invalid query parameter types or unsupported `alignment` enum values.
- **`502 Bad Gateway`**:
  - Upstream Elexon BMRS API returned an error status code.
- **`504 Gateway Timeout`**:
  - Upstream Elexon connection failed or timed out after configured retries.

---

## 3. Running & Testing Locally

### Run Backend Server
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Run Automated Backend Tests
```bash
python -m pytest backend/tests
```
All 41 unit and route tests run **100% offline** in < 1 second using mocked transports.

### Optional: Run Live Elexon Smoke Tests
```bash
# PowerShell:
$env:RUN_LIVE_TESTS="1"; python -m pytest backend/tests/test_elexon_smoke.py
# Bash:
RUN_LIVE_TESTS=1 python -m pytest backend/tests/test_elexon_smoke.py
```

### Run Frontend Build Verification
```bash
npm --prefix frontend run build
```
