# WindCast Analytics

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178c6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646cff.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://www.docker.com/)

A full-stack energy analytics web application designed for UK electricity procurement and trading teams to evaluate day-ahead wind generation forecasts against outturn actuals from the Elexon BMRS Insights Solution for January 2026.

---

## 1. System Architecture

WindCast Analytics supports dual deployment paradigms: a unified multi-container Docker Compose topology for local development/air-gapped evaluation, and a decoupled cloud deployment (Vercel Frontend + Render/Heroku Backend) for zero-cost public access.

### Production Cloud Architecture (Vercel + Render)

```
   Browser Client
         │
         ├─────────────────────────────────────────┐
         ▼                                         ▼
   Vercel Edge Network                      Render Web Service
 (React SPA Static Bundle)              (FastAPI ASGI Python 3.12)
   https://*.vercel.app                   https://*.onrender.com
         │                                         │
         │ Direct REST Requests (CORS Allowed)     │ Upstream Ingestion
         └────────────────────────────────────────►│ (Non-overlapping ≤7-day chunks)
                                                   ▼
                                        Elexon BMRS Insights API
                                      (FUELHH & WINDFOR Endpoints)
```

### Local Container Architecture (Docker Compose)

```
   Browser (Host Machine)
         │
         ├──────► Port 3000: NGINX Web Server (windcast-frontend)
         │           │
         │           ├── Serves compiled React static assets
         │           └── /api/* Reverse Proxy ──┐ (Docker Bridge Network)
         │                                      │
         └──────► Port 8000 (Direct API Access) ▼
                   Uvicorn / FastAPI Backend (windcast-backend)
```

---

## 2. Repository Layout

```text
windcast-analysis/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app, dynamic PORT, CORS middleware & health check
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── evaluation.py           # REST endpoints: /evaluation, /summary, /timeseries, /exclusions
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── elexon.py               # FUELHH and WINDFOR Pydantic models & ingestion audit schemas
│   │   │   └── analysis.py             # Evaluation models, metrics, alignment & config schemas
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── elexon_client.py        # Elexon BMRS client, chunking, retries & deduplication
│   │       └── forecast_evaluator.py   # Day-ahead cutoff evaluation, alignment & metrics engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py              # Health check and CORS origins parsing tests
│   │   ├── test_elexon_client.py       # Chunking, validation, retries & deduplication tests
│   │   ├── test_elexon_smoke.py        # Isolated live API smoke tests (RUN_LIVE_TESTS=1)
│   │   ├── test_forecast_evaluator.py  # Forecast selection, cutoffs, alignment & metric formula tests
│   │   └── test_api.py                 # FastAPI route tests, parameter validation & error handling
│   ├── .env.example                    # Backend environment variable template
│   ├── pytest.ini                      # Pytest marker registration
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Production backend Docker image
│   └── .dockerignore                   # Backend Docker build exclusion rules
├── frontend/
│   ├── src/
│   │   ├── types/
│   │   │   └── evaluation.ts           # Strict TypeScript contracts matching Pydantic schemas
│   │   ├── services/
│   │   │   └── api.ts                  # Typed API client with VITE_API_BASE_URL fallback
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
│   ├── .env.example                    # Frontend environment variable template
│   ├── package.json                    # Node dependencies & Recharts
│   ├── tsconfig.json                   # TypeScript configuration
│   ├── vite.config.ts                  # Vite build & proxy configuration
│   ├── tailwind.config.js              # Tailwind CSS theme configuration
│   ├── vercel.json                     # Vercel SPA routing rewrite rules
│   ├── nginx.conf                      # Production NGINX reverse-proxy configuration
│   ├── Dockerfile                      # Multi-stage production frontend Docker image
│   └── .dockerignore                   # Frontend Docker build exclusion rules
├── docker-compose.yml                  # Root container orchestration
├── render.yaml                         # Render Infrastructure-as-Code blueprint
├── Procfile                            # Heroku/PaaS start command specification
├── .gitignore                          # Version control ignore rules (protects .env files)
└── README.md                           # Documentation & production guide
```

---

## 3. Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Type | Default | Description |
|:---|:---|:---|:---|
| `PORT` | Integer | `8000` | Port on which the Uvicorn ASGI server listens. Injected automatically by PaaS providers (Render, Heroku). |
| `CORS_ORIGINS` | String | `http://localhost:5173, http://127.0.0.1:5173, http://localhost:3000, http://127.0.0.1:3000` | Comma-separated list of allowed origins. In production, set to your deployed Vercel domain (e.g. `https://windcast-analytics.vercel.app`). Wildcards (`*`) are disallowed in production. |

### Frontend Configuration (`frontend/.env`)

| Variable | Type | Default | Description |
|:---|:---|:---|:---|
| `VITE_API_BASE_URL` | String | `""` (empty) | Base URL of the deployed FastAPI backend (e.g. `https://windcast-backend.onrender.com`). When unset, the frontend sends relative `/api/*` requests, which are handled by the Vite dev proxy or Docker NGINX reverse proxy. |

---

## 4. Production Deployment Guide

### Recommended Stack: Vercel (Frontend) + Render (Backend)

This combination qualifies for zero-cost hosting and provides enterprise-grade performance for evaluation.

#### Step 1: Deploy Backend to Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service** (or use **Blueprint** pointing to `render.yaml`).
3. Connect your Git repository.
4. Configure the service:
   - **Name**: `windcast-backend`
   - **Region**: Frankfurt (EU Central) or London (nearest to UK BMRS endpoints)
   - **Branch**: `master` (or your active branch)
   - **Root Directory**: Leave blank (repository root)
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. In **Advanced Settings**, configure:
   - **Health Check Path**: `/api/health`
   - **Environment Variables**:
     - `PYTHON_VERSION`: `3.12.0`
     - `CORS_ORIGINS`: `https://<your-vercel-app-name>.vercel.app` (you can update this after Step 2)
6. Click **Deploy Web Service**.
7. Once deployed, note your service URL: `https://<service-name>.onrender.com`.
8. Verify health: `curl https://<service-name>.onrender.com/api/health`.

> **Note on Free Tier Inactivity**: Render free instances spin down after 15 minutes of inactivity. The initial cold request may take ~50 seconds while the instance initializes. Subsequent requests execute instantly.

---

#### Step 2: Deploy Frontend to Vercel

1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Import your Git repository.
4. In the configuration screen:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Expand **Environment Variables** and add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://<service-name>.onrender.com` (from Step 1, without trailing slash)
6. Click **Deploy**.
7. Vercel will build and deploy the React SPA. Once complete, copy your production domain (e.g., `https://windcast-analytics.vercel.app`).
8. Return to Render and update `CORS_ORIGINS` to include your Vercel domain if not already set.

---

#### Alternative Backend: Heroku Deployment

A `Procfile` is included at the repository root for Heroku compatibility:
```text
web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Deploying to Heroku:
```bash
heroku create windcast-backend
heroku config:set CORS_ORIGINS="https://your-vercel-app.vercel.app"
git push heroku master
```

---

## 5. Docker Containerization & Local Compose

WindCast Analytics includes a complete multi-container Docker configuration for local reproducibility.

### Prerequisites
- Docker Desktop with WSL 2 backend on Windows (or Docker Engine on Linux/macOS).
- Docker daemon running.

### Commands

1. **Build and start containers in the background**:
   ```bash
   docker compose up -d --build
   ```

2. **Verify container health**:
   ```bash
   docker compose ps
   ```
   Both services will report `Up (healthy)`:
   - `windcast-backend`: listens on host port `8000`
   - `windcast-frontend`: listens on host port `3000`

3. **Access the application**:
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Endpoint**: [http://localhost:3000/api/health](http://localhost:3000/api/health)

4. **Inspect service logs**:
   ```bash
   docker compose logs -f
   ```

5. **Stop and remove containers**:
   ```bash
   docker compose down
   ```

---

## 6. Local Development (Without Docker)

### Backend (Python FastAPI)

1. Create and activate a Python 3.12 virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Run the backend test suite:
   ```bash
   python -m pytest backend/tests
   ```

4. Start the development server with live reload:
   ```bash
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Frontend (React + Vite + TypeScript)

1. Install Node dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Verify TypeScript types and production build:
   ```bash
   npm run build
   ```

3. Start Vite development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api/*` calls to `http://127.0.0.1:8000`.

---

## 7. Testing & Quality Assurance

The test suite enforces zero-mock validation on business logic and strict contract integrity:

```bash
# Run all 44 offline unit, contract, and parsing tests:
python -m pytest backend/tests

# Run live Elexon BMRS API smoke tests (requires outbound internet connection):
# Windows PowerShell:
$env:RUN_LIVE_TESTS="1"; python -m pytest backend/tests/test_elexon_smoke.py
# Linux/macOS:
RUN_LIVE_TESTS=1 python -m pytest backend/tests/test_elexon_smoke.py
```

### Test Coverage Highlights
- **`test_elexon_client.py`**: Validates non-overlapping $\le 7$-day chunking across month boundaries, UTC date-range limits, retry backoff on HTTP 429/5xx, and auditable deduplication key `(publishTime, startTime)`.
- **`test_forecast_evaluator.py`**: Proves causality enforcement ($publishTime \le Cutoff(D) < startTime$), latest-forecast selection, physical power averaging ($(SP_{2k-1} + SP_{2k})/2$), and metric accuracy (MAE, RMSE, Signed Bias, MAPE zero-actual exclusion, WMAPE).
- **`test_api.py`**: Tests all 4 REST endpoints (`/evaluation`, `/summary`, `/timeseries`, `/exclusions`), query parameter boundaries, and upstream error mapping (502/504).
- **`test_health.py`**: Tests health check response schemas and CORS origins parsing from `CORS_ORIGINS`.

---

## 8. REST API Specification

All endpoints are rooted under `/api`:

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/health` | Service health status, version, and ISO 8601 UTC timestamp. |
| `GET` | `/api/evaluation` | Full evaluation payload: configuration, metrics, audit breakdown, and aligned observations. |
| `GET` | `/api/evaluation/summary` | Executive summary metrics (MAE, RMSE, Signed Bias, MAPE, WMAPE) and interval counts. |
| `GET` | `/api/evaluation/timeseries` | Aligned observations formatted for chronological charting. |
| `GET` | `/api/evaluation/exclusions` | Exclusions breakdown, missing actuals/forecasts, and raw record counters. |

### Query Parameters

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `start_date` | `YYYY-MM-DD` | `2026-01-01` | Delivery period start date (UTC). |
| `end_date` | `YYYY-MM-DD` | `2026-01-31` | Delivery period end date (UTC, maximum 35-day span). |
| `cutoff_time` | `HH:MM` | `17:00` | Evaluation cutoff time on day $D-1$ in UTC. **Pilot assumption**. |
| `alignment` | String | `HOURLY` | Temporal alignment: `HOURLY` (exact power mean) or `HALF_HOURLY` (forecast broadcast). |
| `use_cache` | Boolean | `true` | When true, caches fetched raw Elexon records to accelerate evaluation. |

---

## 9. Methodology & Pilot Assumptions

1. **Evaluation Cutoff Default (17:00 UTC on $D-1$)**:
   The default 17:00 UTC cutoff on day $D-1$ represents the NGESO operational planning gate closure assumption for pilot evaluation. It is a **pilot default assumption**, not a statutory BSC market deadline. Alternative gates (e.g. 11:00 UTC or 12:00 UTC) are selectable via the UI for sensitivity analysis.
2. **Causality & Look-Ahead Prevention**:
   A forecast is strictly eligible for delivery interval $[T_{\text{start}}, T_{\text{end}})$ on delivery day $D$ if and only if:
   $$publishTime \le \text{Cutoff}(D) < T_{\text{start}}$$
   Any forecast with $T_{\text{start}} \le publishTime$ represents an initialized retrospective hindcast from the numerical weather prediction model and is discarded to eliminate look-ahead bias.
3. **Physical Power Averaging**:
   Because electrical power in Megawatts ($MW$) represents an instantaneous rate of energy flow ($1\text{ MW} = 1\text{ MJ/s}$), the hourly actual generation is the exact arithmetic mean of the two constituent half-hour settlement periods:
   $$\text{Actual}_{\text{hourly}} = \frac{\text{SP}_{2k-1} + \text{SP}_{2k}}{2}$$
   If either half-hour observation is missing from Elexon FUELHH, the entire hourly interval is classified as missing rather than imputed with synthetic data.
4. **Zero-Actual Policy & Error Metrics**:
   - **MAE**: Mean Absolute Error ($\frac{1}{N} \sum |F_t - A_t|$) in MW.
   - **RMSE**: Root Mean Square Error ($\sqrt{\frac{1}{N} \sum (F_t - A_t)^2}$) in MW.
   - **Signed Bias**: Mean Error ($\frac{1}{N} \sum (F_t - A_t)$). Positive indicates overforecasting; negative indicates underforecasting.
   - **MAPE**: Mean Absolute Percentage Error ($\frac{1}{N^*} \sum \frac{|F_t - A_t|}{A_t} \times 100\%$). Intervals where $A_t < 1.0\text{ MW}$ are excluded to avoid zero-division singularities, with the excluded sample count reported explicitly.
   - **WMAPE**: Volume-Weighted Mean Absolute Percentage Error ($\frac{\sum |F_t - A_t|}{\sum A_t} \times 100\%$). Resistant to low-generation distortion and the utility procurement standard.

---

## 10. AI Disclosure & Verification

In accordance with academic and engineering integrity standards:

- **AI Assistance**: This codebase was developed collaboratively with **Google DeepMind's Antigravity** agentic pair programmer.
- **Human Guidance & Oversight**: All architectural decisions, mathematical formulations (causality rules, physical power averaging, metric equations), API response schemas, and validation criteria were specified, reviewed, and approved through a rigorous multi-stage review process (`DEFINE → INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → REFINE`).
- **Data Veracity Guarantee**: No synthetic records, mocked test passes, or hallucinated measurements are used. All live data is ingested directly from the official Elexon BMRS Insights API endpoints (`FUELHH` and `WINDFOR`), with every deduplicated record and excluded interval transparently audited.
