# Phase 2: API Layer & CRUD Implementation

**Status:** ✅ Complete  
**Date:** 2026-04-27  
**Files Modified/Created:** `app/api/v1/health.py`, `app/api/v1/surveys.py`, `app/services/survey_service.py`, `app/models/survey.py`, `alembic/versions/bd49c5f091c7_fix_phase1_debt_extension_default_index.py`

---

## Phase 1 Debt Resolution

All 3 actionable debts from Phase 1 were resolved BEFORE any new code was written:

| Debt | Fix | Migration |
|---|---|---|
| `CREATE EXTENSION IF NOT EXISTS vector` | Added `op.execute(...)` to migration `upgrade()` | `bd49c5f091c7` |
| `is_ordered` missing `server_default` | Added `server_default=sa.text("true")` to ORM model + `op.alter_column(...)` in migration | `bd49c5f091c7` |
| No HNSW index on `prompt_embedding` | Created `ix_survey_cache_embedding_hnsw` with `vector_cosine_ops` via `op.execute(...)` | `bd49c5f091c7` |

Debt #4 (`DATABASE_URL` localhost vs Docker service name) remains deferred to Phase 4 as planned.

---

## What Was Implemented

### 1. Health Check Endpoint (`GET /api/v1/health`)
- Executes `SELECT 1` via the injected `AsyncSession` to probe database connectivity.
- Returns `{"api": "healthy", "database": "healthy"}` or `"unhealthy"` if DB is unreachable.
- Used by Docker healthchecks and external monitoring.

### 2. Survey CRUD Service (`app/services/survey_service.py`)
- `list_surveys()` — Queries all surveys ordered by `created_at DESC`, maps to `SurveyListItem`.
- `get_survey_by_id()` — Fetches by primary key using `scalar_one_or_none()`.
- `save_survey()` — Creates a `Survey` ORM instance, serializes the full payload via `model_dump(mode="json")` into the JSONB `survey_data` column.
- `update_survey()` — Fetches, merges all fields, flushes and refreshes.
- `delete_survey()` — Fetches and deletes, returns boolean for 404 handling.
- Private `_orm_to_response()` helper maps ORM → Pydantic cleanly.

### 3. Survey CRUD Endpoints (`app/api/v1/surveys.py`)
- `GET /api/v1/surveys` — List all surveys (left sidebar).
- `GET /api/v1/surveys/{survey_id}` — Get a specific survey.
- `POST /api/v1/surveys` — Create a manually authored survey.
- `PUT /api/v1/surveys/{survey_id}` — Update an existing survey.
- `DELETE /api/v1/surveys/{survey_id}` — Delete a survey (returns 204).
- `POST /api/v1/surveys/generate` — Stubbed with `501 Not Implemented` for Phase 4.
- All endpoints return proper `404` when resource not found.

### 4. FastAPI Server Running
- Uvicorn started locally with `--reload` for hot-reloading.
- Swagger UI accessible at `http://localhost:8000/docs`.
- All CORS, exception handlers, and rate limiter middleware are wired up.

---

## Bugs Encountered & Fixes

### Bug 1: Alembic autogenerate produced empty migration for `server_default` change
- **Cause:** Alembic's autogenerate cannot detect `server_default` changes — it only detects new/removed tables and columns, not default value modifications.
- **Fix:** Wrote the migration `upgrade()` manually with `op.alter_column()` and `op.execute()`.
- **Rule:** Any migration involving `server_default`, custom SQL (like `CREATE EXTENSION`), or index creation on extension types MUST be written manually.

---

## Verified Final State

### Endpoints Tested

| Endpoint | Method | Status | Response |
|---|---|---|---|
| `/api/v1/health` | GET | ✅ 200 | `{"api": "healthy", "database": "healthy"}` |
| `/api/v1/surveys` | GET | ✅ 200 | Returns list of surveys |
| `/api/v1/surveys` | POST | ✅ 201 | Creates and returns survey with UUID |
| `/api/v1/surveys/{id}` | GET | ✅ 200 | Returns full survey with questions |
| `/api/v1/surveys/{id}` | PUT | ✅ 200 | Updates and returns survey |
| `/api/v1/surveys/{id}` | DELETE | ✅ 204 | Deletes survey |
| `/api/v1/surveys/generate` | POST | ⏳ 501 | Stubbed for Phase 4 |

### Database State
- Migration `bd49c5f091c7` applied on top of `23beccb1c3be`.
- HNSW index `ix_survey_cache_embedding_hnsw` confirmed on `survey_cache.prompt_embedding`.
- `is_ordered` column now has `DEFAULT true`.
- pgvector extension `vector 0.8.2` confirmed active.

---

## Known Technical Debt & Next Steps

| # | Debt | Priority | Phase to Fix |
|---|---|---|---|
| 1 | `DATABASE_URL` uses `localhost` — must change to `db` for Docker Compose deployment | HIGH | Phase 4 |
| 2 | No authentication middleware applied to endpoints yet (auth.py exists but is not wired) | MEDIUM | Phase 3 |
| 3 | Rate limiter is initialized in `main.py` but `@limiter.limit()` decorator is not applied to any route yet | MEDIUM | Phase 3 |
| 4 | `_orm_to_response()` uses `survey_data.get("questions", [])` — does not validate the nested structure against `QuestionSchema` | LOW | Phase 3 |
| 5 | No pagination on `GET /api/v1/surveys` — will be slow with thousands of surveys | LOW | Phase 5 |

---

## Commands Reference

```powershell
# Start FastAPI server locally (with hot-reload)
$env:PYTHONPATH = "."; .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method GET

# Create a test survey
$body = '{"title":{"en":"Test","fr":"Test FR"},"description":{"en":"Desc","fr":"Desc FR"},"is_ordered":true,"questions":[]}' 
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/surveys" -Method POST -Body $body -ContentType "application/json"

# List all surveys
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/surveys" -Method GET

# Swagger UI
# Open http://localhost:8000/docs in browser
```
