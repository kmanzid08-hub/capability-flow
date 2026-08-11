# Capability Flow

Capability Flow is a multi-tenant SaaS foundation for maintaining an organization's people and capability records. This first milestone contains organization registration, JWT authentication, active-membership organization selection, and an isolated People directory.

## Repository map

- `backend/` — FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, and pytest
- `frontend/` — React, TypeScript, Vite, Tailwind, TanStack Query, React Hook Form, and Zod
- `docs/` — architecture, data model, tenancy controls, and roadmap
- `infrastructure/` — reserved for deployment assets beyond local Compose

## Windows PowerShell setup

Prerequisites: Python 3.12, Node.js 20 or newer, and Docker Desktop.

```powershell
docker compose up -d postgres

Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

In a second PowerShell window:

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://localhost:8000/docs`.

## Quality checks

```powershell
Set-Location backend
ruff check .
ruff format --check .
mypy app
pytest

Set-Location ..\frontend
npm run lint
npm test
npm run build
```

The checked-in development credentials are local-only. Replace `JWT_SECRET_KEY` and all database credentials before deployment. Production should terminate TLS at a trusted proxy, restrict CORS, use a managed secret store, and run migrations as an explicit release step.

