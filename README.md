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
│   ├── requirements.txt                # Backend dependencies
│   ├── Dockerfile                      # Production backend Docker image
│   └── .dockerignore                   # Backend Docker build exclusion rules
├── frontend/
│   ├── src/
│   │   ├── types/
│   │   │   └── evaluation.ts           # Strict TypeScript contracts matching Pydantic schemas
│   │   ├── services/
│   │   │   └── api.ts                  # Typed API client with error handling
│   │   ├── components/
│   │   │   ├── Header.tsx              # Application header & live health indicator
│   │   │   ├── ControlBar.tsx          # Date range, evaluation cutoff, and alignment controls
│   │   │   ├── KpiGrid.tsx             # Metric cards (MAE, RMSE, Signed Bias, MAPE, WMAPE)
│   │   │   ├── GenerationChart.tsx     # Interactive Recharts time-series visualization
│   │   │   ├── ExclusionsView.tsx      # Transparency audit & verified CSV export
│   │   │   ├── MethodologyModal.tsx    # Assumptions disclosure & formula definitions
│   │   │   └── ErrorBanner.tsx         # Accessible error presentation
│   │   ├── App.tsx                     # React dashboard root
│   │   ├── main.tsx                    # React DOM entrypoint
│   │   └── index.css                   # Tailwind CSS directives
│   ├── package.json                    # Node dependencies & Recharts
│   ├── tsconfig.json                   # TypeScript configuration
│   ├── vite.config.ts                  # Vite build & proxy configuration
│   ├── tailwind.config.js              # Tailwind CSS theme configuration
│   ├── nginx.conf                      # Production NGINX reverse-proxy configuration
│   ├── Dockerfile                      # Multi-stage production frontend Docker image
│   └── .dockerignore                   # Frontend Docker build exclusion rules
├── docker-compose.yml                  # Root container orchestration
├── .gitignore                          # Version control ignore rules
└── README.md                           # Documentation & API specifications
```

---

## 2. Docker Containerization & Docker Compose

WindCast Analytics is fully containerized using multi-stage production Docker images and unified via Docker Compose.

### Container Architecture & Networking

```
Browser (Host Machine)
   │
   ├──────► Port 3000: NGINX Web Server (windcast-frontend)
   │           │
   │           ├── Static Assets (React SPA bundle)
   │           └── /api/ Reverse Proxy ────┐ (Internal Docker Bridge Network)
   │                                       │
   └──────► Port 8000 (Direct API Access)  ▼
             Uvicorn / FastAPI Backend (windcast-backend)
```

- **Browser-to-Container Isolation**: The user's browser accesses `http://localhost:3000`. The frontend container runs an optimized NGINX server that serves the pre-compiled React static assets and reverse-proxies `/api/` requests internally to `http://backend:8000/api/`. This ensures the browser never needs to resolve internal Docker service names and eliminates CORS issues.
- **Backend Image (`backend/Dockerfile`)**: Python 3.12-slim base image, non-root user (`appuser`), layer-cached `pip install`, and built-in health check probing `/api/health`.
- **Frontend Image (`frontend/Dockerfile`)**: Multi-stage build (Stage 1: Node 22 Alpine build; Stage 2: NGINX Alpine production web server with gzip compression and caching).

---

### Prerequisites
- **Docker Desktop for Windows**: Installed with WSL 2 backend enabled.
- Ensure Docker Desktop is launched and running (status in system tray: green / running).

---

### Docker Compose Commands

1. **Build the container images**:
   ```bash
   docker compose build
   ```

2. **Start the complete stack in the background**:
   ```bash
   docker compose up -d
   ```

3. **Verify running containers and health status**:
   ```bash
   docker compose ps
   ```
   Both `windcast-backend` and `windcast-frontend` will report `Up (healthy)`.

4. **Access the application**:
   - **Frontend Dashboard**: Open [http://localhost:3000](http://localhost:3000) in your browser.
   - **Backend API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).
   - **Health Endpoint**: [http://localhost:3000/api/health](http://localhost:3000/api/health) (via NGINX proxy) or [http://localhost:8000/api/health](http://localhost:8000/api/health) (direct).

5. **Inspect real-time logs**:
   ```bash
   # All services:
   docker compose logs -f
   # Backend service only:
   docker compose logs -f backend
   # Frontend service only:
   docker compose logs -f frontend
   ```

6. **Rebuild after code modifications**:
   ```bash
   docker compose up -d --build
   ```

7. **Stop and remove containers and network**:
   ```bash
   docker compose down
   ```

---

## 3. Local Development (Without Docker)

### Backend (Python FastAPI)
```bash
# 1. Run tests (offline):
python -m pytest backend/tests

# 2. Run optional live smoke tests:
$env:RUN_LIVE_TESTS="1"; python -m pytest backend/tests/test_elexon_smoke.py

# 3. Start local server:
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (React + Vite + TypeScript)
```bash
# 1. Build check:
npm --prefix frontend run build

# 2. Start development server:
npm --prefix frontend run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. Vite automatically proxies `/api` to `http://127.0.0.1:8000`.

---

## 4. API Endpoints Specification

All endpoints are served under `/api`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health status and ISO UTC timestamp. |
| `GET` | `/api/evaluation` | Full evaluation payload: config, metrics, audit, observations. |
| `GET` | `/api/evaluation/summary` | High-level summary KPIs (MAE, RMSE, Signed Bias, MAPE, WMAPE). |
| `GET` | `/api/evaluation/timeseries` | Chronological time-series observations formatted for charts. |
| `GET` | `/api/evaluation/exclusions` | Exclusions audit, missing intervals, and ingestion counters. |

### Query Parameters

- `start_date`: Delivery start date (default `2026-01-01`).
- `end_date`: Delivery end date (default `2026-01-31`, max 35 days).
- `cutoff_time`: Evaluation cutoff time on day $D-1$ in UTC (default `17:00` is a pilot assumption).
- `alignment`: `HOURLY` (exact power mean) or `HALF_HOURLY` (broadcast).
- `use_cache`: `true` or `false` (uses server-side cache for fast reloading).

---

## 5. Methodology & Assumptions Summary

1. **Pilot Default Cutoff**: 17:00 UTC on day $D-1$ is implemented as a configurable pilot default rather than a verified statutory market deadline.
2. **Causality & Look-Ahead Prevention**: Forecasts must satisfy `publishTime <= Cutoff(D) < startTime`. Any retrospective hindcasts (`startTime <= publishTime`) are discarded.
3. **Physical Hourly Averaging**: Because power in Megawatts ($MW$) is a rate of energy delivery, hourly actual is the exact mean of the two constituent half-hours:
   $$\text{Actual}_{\text{hourly}} = \frac{\text{SP}_1 + \text{SP}_2}{2}$$
4. **MAPE Zero-Actual Policy**: Excludes intervals where actual outturn $< 1.0\text{ MW}$ to avoid division-by-zero explosions. Reports excluded count explicitly.
