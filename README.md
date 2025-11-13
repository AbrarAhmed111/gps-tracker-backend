# FastAPI Backend Template

A clean, minimal FastAPI starter to build backend APIs that connect to a Next.js app.

## Quickstart

1) Install dependencies
```bash
pip install -r requirements.txt
```

2) Create `.env` (or set env vars)
```env
ENVIRONMENT=development
BASE_URL=http://localhost:8000
API_VERSION=1.0.0
ALLOWED_ORIGINS=*  # or http://localhost:3000 for Next.js
```

3) Run the server
```bash
uvicorn api.main:app --reload
```

Open: http://localhost:8000

## Documentation
- File‑by‑file explanations: `docs/PROJECT_STRUCTURE.md`

## Endpoints
- GET `/`       → basic info
- GET `/health` → health check
- GET `/api/ping` → returns `{ "pong": true }`
- POST `/api/echo` → echoes JSON payload
- POST `/api/ai/fibonacci` → compute first N Fibonacci numbers
- POST `/api/ai/wordcount` → word frequency counts for text
- POST `/api/ai/normalize` → min-max normalize numeric array

## CORS for Next.js
Set `ALLOWED_ORIGINS` to your Next.js URL, e.g.:
```
ALLOWED_ORIGINS=http://localhost:3000
```

## Deploy (Railway)
- Repo contains `Procfile` and `railway.json`
- Set the same env vars on your Railway service
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

## Project Structure
```
.
├── api/
│   └── main.py           # FastAPI app entry
├── config.py             # Minimal config helpers
├── requirements.txt      # Dependencies
├── Procfile              # Railway start command
├── railway.json          # Railway config
└── runtime.txt           # Python version
```

## Notes
- Designed to be a reusable backend template
- Add routers under `/api` and keep `config.py` generic

