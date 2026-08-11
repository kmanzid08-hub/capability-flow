.PHONY: install db migrate backend frontend test lint
install:
	cd backend && python -m pip install -e ".[dev]"
	cd frontend && npm install
db:
	docker compose up -d postgres
migrate:
	cd backend && alembic upgrade head
backend:
	cd backend && uvicorn app.main:app --reload
frontend:
	cd frontend && npm run dev
test:
	cd backend && pytest
	cd frontend && npm test
lint:
	cd backend && ruff check . && ruff format --check . && mypy app
	cd frontend && npm run lint && npm run build

