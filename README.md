# GPS Simulation System (FastAPI Microservice)

FastAPI backend for the GPS Simulation System, exposing Python logic for a Next.js app (no DB). Includes Excel processing, geocoding (Google Maps), simulation, and route analysis APIs.

## Quickstart (Windows PowerShell)

1) Create and activate venv, install deps
```powershell
cd D:\TORRENT\Devwebies\gps-tracker-backend
py -m venv .venv
.\.venv\Scripts\Activate
py -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Create `.env` (or set env vars)
```env
ENVIRONMENT=development
BASE_URL=http://localhost:8000
API_VERSION=1.0.0
ALLOWED_ORIGINS=http://localhost:3000
```

3) Run the server
```powershell
py -m uvicorn api.main:app --reload
```

Open: http://localhost:8000 (Swagger UI: /docs, ReDoc: /redoc)

## Documentation
- File‑by‑file explanations: `docs/PROJECT_STRUCTURE.md`

## Key Endpoints
- Core
  - GET `/` → basic info
  - GET `/health` → health check
  - GET `/api/ping` → `{ "pong": true }`
  - POST `/api/echo` → echoes JSON

- AI examples
  - POST `/api/ai/fibonacci` → compute first N Fibonacci numbers
  - POST `/api/ai/wordcount` → word frequency
  - POST `/api/ai/normalize` → min–max normalize numbers

- v1 (spec-aligned)
  - Excel
    - POST `/api/v1/excel/process`
    - POST `/api/v1/excel/validate`
  - Geocoding (api_key comes from request body)
    - POST `/api/v1/geocoding/geocode`
    - POST `/api/v1/geocoding/batch`
  - Simulation
    - POST `/api/v1/simulation/calculate-position`
    - POST `/api/v1/simulation/calculate-positions-batch`
  - Routes
    - POST `/api/v1/routes/analyze`
    - POST `/api/v1/routes/validate`
  - Utils
    - POST `/api/v1/utils/checksum`
  - Health/Version
    - GET `/api/v1/health`
    - GET `/api/v1/version`

## Request examples
- Geocode (single)
```json
POST /api/v1/geocoding/geocode
{
  "address": "F-10 Markaz, Islamabad, Pakistan",
  "api_key": "YOUR_GOOGLE_MAPS_API_KEY",
  "language": "en",
  "region": "pk"
}
```

- Geocode (batch)
```json
POST /api/v1/geocoding/batch
{
  "api_key": "YOUR_GOOGLE_MAPS_API_KEY",
  "addresses": [
    { "id": "w1", "address": "Blue Area, Islamabad" },
    { "id": "w2", "address": "Saidpur Village, Islamabad" }
  ],
  "language": "en",
  "region": "pk"
}
```

## CORS for Next.js
Set `ALLOWED_ORIGINS` to your Next.js URL, e.g.:
```
ALLOWED_ORIGINS=http://localhost:3000
```

## Deploy (Railway)
- Repo contains `Procfile` and `railway.json`
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Set env vars: `ENVIRONMENT, BASE_URL, API_VERSION, ALLOWED_ORIGINS`
- No Google Maps key in env (the client passes `api_key` per request)

## Project Structure
```
.
├── api/
│   ├── main.py                 # FastAPI app entry (mounts routers)
│   ├── __init__.py
│   ├── routers/
│   │   ├── ai.py               # small AI/Python examples
│   │   ├── v1_excel.py         # /api/v1/excel
│   │   ├── v1_geocoding.py     # /api/v1/geocoding
│   │   ├── v1_simulation.py    # /api/v1/simulation
│   │   ├── v1_routes.py        # /api/v1/routes
│   │   └── v1_health.py        # /api/v1/health, /version
│   └── schemas/
│       ├── excel_schemas.py
│       ├── geocoding_schemas.py
│       └── simulation_schemas.py
├── services/
│   ├── ai.py
│   ├── excel_processor.py
│   ├── geocoding_service.py
│   ├── position_simulator.py
│   ├── route_calculator.py
│   └── interpolation_service.py
├── utils/
│   ├── checksum.py
│   ├── date_utils.py
│   ├── geo_math.py
│   └── validators.py
├── docs/PROJECT_STRUCTURE.md
├── config.py
├── start_api_server.py
├── requirements.txt
├── Procfile
├── railway.json
└── runtime.txt
```

## Notes
- No database; Next.js handles DB and auth.
- Geocoding key is client-provided in request body (not env).

