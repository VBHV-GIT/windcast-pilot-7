# WindCast Analytics

A full-stack web application designed for UK electricity procurement teams to evaluate wind generation forecasts against outturn actuals from the Elexon BMRS Insights Solution for January 2026.

---

## 1. Project Structure

```text
windcast-analysis/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI application & /health endpoint
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py       # Automated health check tests
│   └── requirements.txt         # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root React component
│   │   ├── main.tsx             # React entrypoint
│   │   └── index.css            # Tailwind CSS directives
│   ├── package.json             # Frontend Node dependencies
│   ├── tsconfig.json            # TypeScript configuration
│   ├── vite.config.ts           # Vite build & proxy configuration
│   └── tailwind.config.js       # Tailwind CSS theme configuration
├── .gitignore                   # Version control ignore rules
└── README.md                    # Setup & documentation
```

---

## 2. Local Setup & Running Instructions

### Prerequisites
- **Python**: Version 3.12+
- **Node.js**: Version 20+ (v22 installed)
- **npm**: Version 10+

---

### Backend Service (FastAPI)

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend development server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The interactive API docs will be available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

5. **Run backend automated tests**:
   ```bash
   python -m pytest tests/
   ```

---

### Frontend Service (React + Vite + TypeScript)

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173) in your browser.

4. **Build for production**:
   ```bash
   npm run build
   ```

---

## 3. Technology Stack

- **Backend**: Python 3.12, FastAPI, Pydantic, HTTPX, Pytest
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React
- **Data Source**: Elexon BMRS Insights API (`FUELHH` and `WINDFOR` datasets)
