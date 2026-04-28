# Phase 3: Middleware Hardening (Auth, Soft Delete, Rate Limiting)

**Status:** ✅ Complete  
**Date:** 2026-04-27  
**Files Modified/Created:** `app/middleware/auth.py`, `app/api/v1/surveys.py`, `app/services/survey_service.py`, `app/models/survey.py`, `.env.example`, `alembic/versions/89a1da1104f9_add_soft_delete_columns.py`

---

## Phase 2 Debt Resolution

| Debt | Fix |
|---|---|
| Auth middleware not wired to endpoints | Implemented Option B auth + added `Depends(verify_bearer_token)` to all routes |
| Rate limiter not applied to routes | Rate limiter initialized in `main.py`; endpoint-level `@limiter.limit()` deferred to Phase 4 (generation endpoint only needs it) |

---

## What Was Implemented

### 1. Bearer Token Authentication — Option B (Disabled by Default)
- **File:** `app/middleware/auth.py`
- When `API_BEARER_TOKEN=disabled` in `.env` (the default in `.env.example`), auth is completely skipped — zero friction for interviewers.
- When set to any other value, every request must include `Authorization: Bearer <token>` header.
- Missing token → `401 Unauthorized`
- Wrong token → `401 Unauthorized`
- Auth is applied via FastAPI `Depends(verify_bearer_token)` on every route in `surveys.py`.
- Uses `HTTPBearer(auto_error=False)` so we can return a descriptive 401 instead of a generic 403.

### 2. Soft Delete
- **Model changes:** Added `is_deleted` (Boolean, default=false) and `deleted_at` (nullable timestamp) to `Survey`.
- **Service changes:** All queries now filter with `Survey.is_deleted == False`.
- **Delete behavior:** `delete_survey()` sets `is_deleted=True` and `deleted_at=now()` instead of removing the row.
- **Migration:** `89a1da1104f9` adds both columns with `server_default=false` so existing rows are unaffected.

### 3. Restore Endpoint
- **Route:** `PATCH /api/v1/surveys/{id}/restore`
- Finds surveys where `is_deleted=True`, flips `is_deleted` back to `False`, clears `deleted_at`.
- Returns the full restored survey response.
- Returns 404 if the survey doesn't exist or is not currently deleted.

### 4. .env.example Updated
- `API_BEARER_TOKEN` default changed from `your-secret-bearer-token-here` to `disabled`.
- Added comments explaining the Option B behavior.

### 5. BACKEND_README.md Created
- Comprehensive project README documenting setup, env vars, all endpoints, auth behavior, HNSW index tuning, and architecture.
- Documents single-token auth scope limitation and recommends JWT for production multi-tenant use.
- Documents HNSW default parameters (`m=16`, `ef_construction=64`) and their trade-offs.

---

## Bugs Encountered & Fixes

### Bug 1: Alembic autogenerate detected false-positive HNSW index removal
- **Cause:** Alembic doesn't understand pgvector's HNSW index type. Every time autogenerate runs, it sees the HNSW index as "unknown" and tries to drop it.
- **Fix:** Manually removed the `op.drop_index('ix_survey_cache_embedding_hnsw')` line from the generated migration.
- **Rule:** After EVERY autogenerate, inspect the migration file and remove any false-positive operations on pgvector indexes.

### Bug 2: Global 404 handler was eating endpoint-specific error messages
- **Cause:** `app/core/exceptions.py` had a `@app.exception_handler(404)` that returned a hardcoded generic message for ALL 404s, overriding the `detail` from endpoint `HTTPException(404)` calls.
- **Fix:** Changed to `getattr(exc, "detail", "The requested resource was not found.")` so endpoint-specific messages pass through.

### Bug 3: Uvicorn hot-reload did not pick up service file changes
- **Cause:** `watchfiles` detected changes in `surveys.py` but did not reload after `survey_service.py` was modified.
- **Fix:** Full server restart (`Ctrl+C` + re-run). This is a known watchfiles issue on Windows.
- **Rule:** After modifying multiple files, always verify the server reloaded by checking server logs or restarting manually.

---

## Verified Final State

### Auth Tests
| Scenario | Result |
|---|---|
| Request without token (auth enabled) | ✅ 401 Unauthorized |
| Request with correct token | ✅ 200 OK |
| Request with wrong token | ✅ 401 Unauthorized |

### Soft Delete & Restore Tests
| Scenario | Result |
|---|---|
| `DELETE /surveys/{id}` | ✅ 204 No Content |
| Survey row in DB after delete | ✅ `is_deleted=true`, `deleted_at` populated |
| `GET /surveys` after delete | ✅ Returns empty list (soft-deleted survey hidden) |
| `GET /surveys/{id}` after delete | ✅ 404 Not Found |
| `PATCH /surveys/{id}/restore` | ✅ 200 OK — returns full restored survey |
| `GET /surveys` after restore | ✅ Survey reappears in list |

### Database State
- Migration `89a1da1104f9` applied (soft delete columns).
- `surveys` table now has `is_deleted BOOLEAN DEFAULT false` and `deleted_at TIMESTAMPTZ`.
- HNSW index still intact on `survey_cache.prompt_embedding`.

---

## Known Technical Debt & Next Steps

| # | Debt | Priority | Phase to Fix |
|---|---|---|---|
| 1 | `DATABASE_URL` uses `localhost` — must change to `db` for Docker Compose | HIGH | Phase 4 |
| 2 | `@limiter.limit()` not applied to generation endpoint | MEDIUM | Phase 4 |
| 3 | `_orm_to_response()` doesn't validate nested question structure against schema | LOW | Phase 5 |
| 4 | No pagination on `GET /surveys` | LOW | Phase 5 |
| 5 | Alembic autogenerate produces false-positive HNSW index drops — needs `include_object` filter | LOW | Phase 5 |
| 6 | Health endpoint has no auth — intentional for Docker healthchecks, but should be documented | LOW | N/A |

---

## Commands Reference

```powershell
# Test auth rejection (no token, when auth is enabled)
try { Invoke-RestMethod -Uri "http://localhost:8000/api/v1/surveys" -Method GET } catch { $_.Exception.Response.StatusCode }

# Test auth success
$headers = @{ Authorization = "Bearer boundary-dev-token-2024" }
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/surveys" -Method GET -Headers $headers

# Verify soft-deleted rows in DB
docker exec boundary_db psql -U boundary -d boundary_surveys -c "SELECT id, title_en, is_deleted, deleted_at FROM surveys;"
```
