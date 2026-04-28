# Phase 4: AI Integration — Implementation Log

**Date:** 2026-04-27  
**Status:** ✅ Complete

---

## What Was Implemented

### 1. Schema Layer (`backend/app/schemas/survey.py`)
- Added `QualityIssue` — structured quality concern with `issue_type`, `question_id`, `severity`, `message_en`, `message_fr`
- Added `CriticResponse` — Structured Output envelope for Agent 2 (`issues: List[QualityIssue]`)
- Added `question_count: Optional[int]` to `GenerateSurveyRequest` (nullable — AI decides if not provided)
- Added `quality_issues: Optional[List[QualityIssue]]` to `SurveyResponse` (null=not audited, []=clean)
- Added `has_quality_issues: bool` to `SurveyListItem` for sidebar rendering

### 2. Model + Migration (`backend/app/models/survey.py`)
- Added `quality_issues` JSONB column (nullable) to `Survey`
- Migration: `bcd8398dc1a7_add_quality_issues_column.py`
- Manually removed false-positive HNSW index drop (known Alembic/pgvector bug)

### 3. Semantic Cache (`backend/app/services/cache/semantic_cache.py`)
- `embed_prompt()` — calls `text-embedding-3-small`, returns 1536-dim vector
- `find_similar_survey()` — pgvector cosine distance query: `1 - (prompt_embedding <=> :embedding) > threshold`
- `store_in_cache()` — inserts prompt + embedding + JSONB into `survey_cache`
- **Cache scope: Global** — no user accounts in current system. In a multi-tenant system, scope by org/user ID

### 4. Prompt Engineering (`backend/app/services/ai/prompts.py`)
- `build_generator_system_prompt(modality)` — three distinct system prompts:
  - **Zero-to-One:** full survey synthesis, diverse types, bilingual
  - **Hybrid Expansion:** keep existing questions, add complementary ones
  - **Translation-Only:** preserve all questions, add/fix bilingual text
- `build_generator_user_prompt()` — includes prompt, `question_count` hint, serialized existing questions
- `build_critic_prompt()` — full quality rubric covering bias, fatigue, translation, type distribution

### 5. Generator Agent (`backend/app/services/ai/generator.py`)
- `generate_survey_with_llm()` — calls `openai.beta.chat.completions.parse(response_format=SurveySchema)`
- Tenacity retry: 3 attempts, exponential backoff (2s → 10s)
- Temperature: 0.7 for creativity

### 6. Critic Agent (`backend/app/services/ai/critic.py`)
- `run_critic_audit()` — fully async background task with its own DB session
- Evaluates both question-level and survey-level issues
- Writes `quality_issues` JSONB after evaluation
- **Trigger policy:** Auto-runs on AI-generated surveys (cache misses only). Manual trigger via `POST /api/v1/surveys/{id}/audit`
- Temperature: 0.3 for consistent evaluation
- Non-fatal: exceptions are logged but never propagate to the user

### 7. Generation Orchestrator (`backend/app/services/generation_service.py`)
- `determine_modality()` — Zero-to-One / Hybrid / Translation-Only detection
- Cache lookup runs for Zero-to-One only (Hybrid and Translation are context-dependent)
- Critic dispatched only on cache misses (cached surveys already audited)
- Auto-saves every generated survey to `surveys` table

### 8. API Endpoints (`backend/app/api/v1/surveys.py`)
- `POST /api/v1/surveys/generate` — rate limited (`10/minute` by IP), full Tri-Modal pipeline
- `POST /api/v1/surveys/{id}/audit` — manual Critic trigger for any survey

### 9. Rate Limiter (`backend/app/main.py`)
- `SlowAPIMiddleware` added
- `RateLimitExceeded` exception handler registered
- `@limiter.limit(settings.RATE_LIMIT)` on `/generate` only

---

## Bugs Hit + Exact Fixes

### Bug 1: Rate limiter caused 500 on every request
**Root cause:** Decorator order. `@limiter.limit()` was placed above `@router.post()`. Slowapi requires it below.  
**Fix:** Swapped decorator order to `@router.post()` first, `@limiter.limit()` second.

### Bug 2: SlowAPIMiddleware not wired
**Root cause:** Phase 3 only set `app.state.limiter` but never added `SlowAPIMiddleware` or the `RateLimitExceeded` exception handler.  
**Fix:** Added both to `main.py`.

### Bug 3: 500 exception handler swallowed tracebacks
**Root cause:** `logger.exception(..., exc_info=exc)` in an async handler has no active exception context — the logger prints nothing.  
**Fix:** Changed to `traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)`.

### Bug 4: Generator stub imported `build_generator_prompt` which didn't exist
**Root cause:** The function name in `prompts.py` was `build_generator_system_prompt` + `build_generator_user_prompt`.  
**Fix:** Corrected the import in `generator.py`.

### Bug 5: `find_similar_survey` embedding format
**Root cause:** pgvector expects the embedding as a string representation of a list (e.g. `"[0.1, 0.2, ...]"`), not a Python list directly when using raw SQL `text()`.  
**Fix:** Pass `str(embedding)` to the SQL parameter.

---

## Known Technical Debt

1. **`quality_issues=null` is ambiguous on cache hits.** When a cached survey is returned, its `quality_issues` is from the original saved copy (may be null if Critic hasn't run yet). Frontend Phase 5 should handle null gracefully with a "Not yet audited" state.

2. **Critic creates a new DB engine per invocation.** The `create_async_engine(db_url, pool_size=1)` in `critic.py` is intentional (background task needs its own connection), but at high volume this creates engine churn. Future fix: use a shared background worker pool.

3. **No Critic on Translation-Only cache.** Translation-Only and Hybrid results are not cached (context-dependent), so they always go through the LLM and always trigger the Critic. But if the same translated survey is saved manually, the Critic won't re-run automatically — only via the audit endpoint.

4. **`SIMILARITY_THRESHOLD = 0.95`** is conservative. In production, tune this empirically. Lower values (e.g., 0.85) trade cache accuracy for hit rate. Documented in README.

---

## Verified Final State

```
POST /api/v1/surveys/generate
  - Zero-to-One: ✅ LLM call → auto-save → cache store → Critic dispatched
  - Cache hit: ✅ No LLM call, no Critic dispatch, instant response
  - Response shape: id, survey, cache_hit, modality

POST /api/v1/surveys/{id}/audit
  - ✅ Returns current survey immediately, Critic runs in background

GET /api/v1/surveys
  - ✅ has_quality_issues present on all items

GET /api/v1/surveys/{id}
  - ✅ quality_issues present (null if not yet audited)
```

---

## Command Reference

```bash
# Run server
PYTHONPATH=. .venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Generate a survey (Zero-to-One)
curl -X POST http://localhost:8000/api/v1/surveys/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Customer satisfaction survey for an online store"}'

# Generate with question count
curl -X POST http://localhost:8000/api/v1/surveys/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Employee onboarding survey", "question_count": 8}'

# Manually trigger Critic audit
curl -X POST http://localhost:8000/api/v1/surveys/{id}/audit

# Apply migration
PYTHONPATH=. .venv/Scripts/alembic upgrade head
```
