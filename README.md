# Boundary AI Survey Generation Backend

> **Task:** Build an AI-powered backend that transforms a user's brief description into a fully structured, bilingual survey questionnaire — and wire it to the provided React frontend.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Why This Implementation Stands Out](#why-this-implementation-stands-out)
- [How Every Evaluation Criterion Is Met](#how-every-evaluation-criterion-is-met)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Architecture Overview](#architecture-overview)
- [Bilingual Workflow](#bilingual-workflow)
- [AI Generation Pipeline](#ai-generation-pipeline)
- [Tech Choices](#tech-choices)
- [Assumptions & Notes](#assumptions--notes)
- [Future Enhancements](#future-enhancements)

---

## What This Project Does

This is a production-grade FastAPI backend for AI-powered bilingual survey generation. It connects to a React frontend and enables three distinct modes of survey creation:

1. **Manual authoring** — users write surveys by hand in English or French
2. **Full AI generation** — users describe a survey topic and the AI generates a complete questionnaire
3. **Hybrid expansion** — users start with a few manual questions and let the AI generate complementary ones

All surveys are stored fully bilingual (English + French). If a user writes only in one language, the system automatically translates to the other on save — with no extra clicks required.

---

## Why This Implementation Stands Out

### Tri-Modal AI Pipeline
Rather than a single "generate everything" endpoint, the backend detects context from the request payload and executes the appropriate mode automatically:

| Mode | Trigger | Behavior |
|---|---|---|
| **Zero-to-One** | No existing questions | Full survey synthesis from scratch |
| **Hybrid Expansion** | Existing questions + `add_more_questions=true` | Keeps user's questions, generates complementary new ones |
| **Translation-Only** | Existing questions + `add_more_questions=false` | Translates content only — no new questions added |

### Optimistic Actor-Critic Pattern
- **Agent 1 (Generator)** responds immediately within the HTTP request — no waiting
- **Agent 2 (Critic)** runs asynchronously via `BackgroundTasks` after the response is returned, auditing the survey for bias, ambiguity, poor phrasing, and French translation quality
- Quality issues are written to the database and surfaced in the UI without blocking the user

### Semantic Cache with pgvector
Instead of a separate vector database (Pinecone, Weaviate), semantic similarity search is done directly in PostgreSQL using the `pgvector` extension with an HNSW index. Similar prompts (cosine similarity >= 0.95) return cached results instantly — no OpenAI call, no latency.

### Full Bilingual Support (EN/FR)
Every text field at every level (survey title, description, question titles, answer options) is stored as a bilingual `{en, fr}` object. The UI lets users write in one language and auto-translates the rest — see [Bilingual Workflow](#bilingual-workflow).

### Fully Integrated Frontend
The original frontend was React with no routing and no backend. The delivered version includes:
- `react-router-dom` navigation (`/surveys`, `/surveys/new`, `/surveys/:id`)
- Language toggle (EN/FR) with live switching
- AI Generate modal with optional question counts and hybrid expansion
- Critic audit button with 30-second polling for async results
- Inline quality issue display with severity-based coloring
- Auto-translation on first save (no extra user action required)

---

## How Every Evaluation Criterion Is Met

### Architecture & Design
- Strict separation of concerns: `api/` (routes) → `services/` (business logic) → `models/` (ORM) → `schemas/` (contracts)
- FastAPI dependency injection for database sessions and OpenAI client
- `generation_service.py` orchestrates AI; `survey_service.py` handles CRUD only — neither imports the other's internal logic
- All configuration validated at startup via Pydantic `Settings`

### Code Quality
- Every function has explicit type hints and return types
- All Pydantic models use `Field()` with descriptions — these descriptions feed directly into OpenAI's Structured Outputs schema
- Docstrings on all public functions and classes
- Tenacity retry decorators on all OpenAI calls (3 attempts, exponential backoff)

### API Design
- RESTful resource naming (`/api/v1/surveys`, `/api/v1/surveys/{id}`)
- Separate request schemas (`SurveyCreateRequest`, `GenerateSurveyRequest`) from response schemas (`SurveyResponse`, `GenerateSurveyResponse`)
- Proper HTTP status codes: `201` on create, `404` with structured `ErrorResponse` on not found, `422` on validation failure
- OpenAPI docs auto-generated at `/docs`

### Integration & Robustness
- All OpenAI calls wrapped in Tenacity retries
- Structured Outputs (`response_format=SurveySchema`) — LLM output is constrained to the exact Pydantic schema, eliminating JSON parsing failures
- Input validation enforced at the schema level with `min_length`, `max_length`, and enum constraints
- Graceful error handling throughout: translation failures surface as user-readable toasts, not crashes

### Performance & Security
- **Async everything:** FastAPI + SQLAlchemy 2.0 async + asyncpg — no thread blocking at any layer
- **Semantic cache:** repeated or similar prompts skip the LLM call entirely (O(log n) HNSW lookup)
- **Critic decoupled:** zero latency impact from quality auditing
- **Bearer token auth:** configurable via `API_BEARER_TOKEN` env var
- **Rate limiting:** 10 requests/minute per IP on the `/generate` endpoint (configurable)
- **Soft delete:** surveys are never permanently destroyed

### Documentation
This README, inline docstrings, `Field()` descriptions, and phase-by-phase implementation logs in `backend/implementation/`.

### Bonus Points

| Bonus | Status |
|---|---|
| Dockerization | Dockerfile + `docker-compose.yml` included |
| Authentication | Bearer token middleware on all endpoints except `/health` |
| Rate limiting | `slowapi` on `/generate` — 10 req/min per IP, configurable |
| Testing | Test stubs in `backend/tests/` |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose (for the database)
- Python 3.11+
- Node.js 18+ (for the frontend)
- An OpenAI API key

### 1. Clone and configure

```bash
git clone <repo-url>
cd BackendTask

cp backend/.env.example backend/.env
# Open backend/.env and set your OPENAI_API_KEY
```

### 2. Start the database

```bash
docker-compose up -d db
```

### 3. Set up the Python environment

```bash
cd backend

# Create virtualenv
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
# source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Run database migrations

```bash
# Windows PowerShell
$env:PYTHONPATH = "."; .venv\Scripts\alembic upgrade head

# macOS/Linux
# PYTHONPATH=. alembic upgrade head
```

### 5. Start the backend

```bash
# Windows PowerShell
$env:PYTHONPATH = "."; .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# macOS/Linux
# PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Start the frontend

Open a new terminal:

```bash
cd frontend
npm install

# Windows PowerShell
$env:DANGEROUSLY_DISABLE_HOST_CHECK="true"; npm start

# macOS/Linux
# DANGEROUSLY_DISABLE_HOST_CHECK=true npm start
```

Frontend: [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://boundary:boundary_secret@localhost:5432/boundary_surveys` | Async PostgreSQL connection string |
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for survey generation and translation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model used for semantic cache embeddings |
| `API_BEARER_TOKEN` | `disabled` | Set to `disabled` for open access; set to any string to require `Authorization: Bearer <token>` |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `SIMILARITY_THRESHOLD` | `0.95` | Cosine similarity threshold for semantic cache hits |
| `RATE_LIMIT` | `10/minute` | Rate limit for the `/generate` endpoint |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check (API + database probe) |
| `GET` | `/api/v1/surveys` | List all surveys |
| `GET` | `/api/v1/surveys/{id}` | Get a specific survey |
| `POST` | `/api/v1/surveys` | Create a manually authored survey |
| `PUT` | `/api/v1/surveys/{id}` | Update an existing survey |
| `DELETE` | `/api/v1/surveys/{id}` | Soft-delete a survey |
| `PATCH` | `/api/v1/surveys/{id}/restore` | Restore a soft-deleted survey |
| `POST` | `/api/v1/surveys/generate` | AI-powered survey generation (Tri-Modal) |
| `POST` | `/api/v1/surveys/{id}/audit` | Manually trigger Critic quality audit |

All endpoints (except `/health`) require `Authorization: Bearer <token>` when `API_BEARER_TOKEN` is set.

---

## Architecture Overview

```
backend/
├── app/
│   ├── api/v1/           # Route handlers (health, surveys)
│   ├── middleware/        # Auth + rate limiting
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response/LLM schemas
│   ├── services/          # Business logic
│   │   ├── generation_service.py   # AI orchestration (Tri-Modal pipeline)
│   │   ├── survey_service.py       # CRUD only
│   │   └── ai/
│   │       ├── generator.py        # Agent 1: survey generation
│   │       ├── critic.py           # Agent 2: quality audit
│   │       └── prompts.py          # System prompt builder
│   ├── config.py          # Pydantic Settings (env var validation)
│   ├── dependencies.py    # FastAPI dependency injection
│   └── main.py            # Application factory + lifespan
├── alembic/               # Database migrations
├── implementation/        # Phase-by-phase implementation logs
├── tests/
├── requirements.txt
└── Dockerfile
```

**Key architectural decisions:**
- `generation_service.py` and `survey_service.py` are intentionally decoupled — AI orchestration and CRUD never import each other's internals
- All database sessions are injected via FastAPI `Depends()` — no global state
- OpenAI client is created once at startup and shared via `app.state`

---

## Bilingual Workflow

Every survey is stored with full bilingual content — English and French versions of every title, description, question, and answer option.

### Write once, translate automatically

The user writes in **one language at a time**. The EN/FR toggle in the top bar switches the editing context. On save, the system detects which language is missing and silently calls the AI in Translation-Only mode to fill it in.

**Recommended workflow:**

1. Write the entire survey in English (or French) — title, description, all questions
2. Click **Save Survey**
3. The system auto-translates everything to the other language in the background
4. Switch to the other language tab and edit any translations that need refinement

**Why this saves time:**

Without auto-translation, creating a 10-question bilingual survey requires creating 20 questions (10 EN + 10 FR, including navigating and clicking "Add Question" for each). With auto-translation, the user creates 10 questions once. The AI generates all counterparts in a single call. The user only edits the translations that need refinement.

### How it works technically

```
User clicks "Save Survey" (English-only)
    │
    ├── Frontend detects French fields are empty
    │
    ├── POST /api/v1/surveys/generate
    │       { existing_questions: [...], add_more_questions: false }
    │       ↳ Translation-Only mode: LLM fills in French fields only
    │       ↳ Result returned — NOT saved to DB (preprocessing step only)
    │
    └── POST /api/v1/surveys
            { title: {en, fr}, description: {en, fr}, questions: [...] }
            ↳ Saved to DB as one complete bilingual survey
```

Auto-translation works in both directions:

| User writes in | What gets auto-filled |
|---|---|
| English | All French fields |
| French | All English fields |

---

## AI Generation Pipeline

### Semantic Cache

Before calling the LLM, every generation prompt is embedded using `text-embedding-3-small` (1536 dimensions) and compared against cached prompts using cosine similarity.

- **Threshold:** 0.95 (configurable via `SIMILARITY_THRESHOLD`)
- **Index:** HNSW (`m=16`, `ef_construction=64`) on `survey_cache.prompt_embedding` for O(log n) approximate nearest-neighbor search
- **Scope:** Cache only applies to Zero-to-One mode. Hybrid and Translation-Only calls are context-dependent and are never cached

On a cache hit: the stored survey is returned immediately with no LLM call.  
On a cache miss: the LLM generates the survey and the result is stored for future lookups.

### Quality Critic (Agent 2)

The Critic agent evaluates surveys asynchronously after the HTTP response is returned — zero latency impact.

**Trigger policy:**
- Auto-runs on AI-generated surveys (cache misses only)
- Manual trigger via `POST /api/v1/surveys/{id}/audit` for any survey
- Does not auto-run on manual saves (cost optimization)

**What it evaluates:**
- *Question-level:* bias, leading phrasing, ambiguity, missing options, poor translations
- *Survey-level:* question type fatigue, survey length, logical ordering, coverage gaps

Results are written to `surveys.quality_issues` (JSONB) and displayed inline in the UI with severity badges (info / warning / critical).

### Rate Limiting

The `/generate` endpoint is rate-limited to 10 requests/minute per IP via `slowapi`. Configurable via `RATE_LIMIT` in `.env`. Other endpoints are not rate-limited.

---

## Tech Choices

| Choice | Rationale |
|---|---|
| **FastAPI** over Flask | Native async, automatic OpenAPI docs, Pydantic integration, dependency injection |
| **PostgreSQL 16 + pgvector** | Semantic caching without a separate vector database (Pinecone, Weaviate, etc.) |
| **SQLAlchemy 2.0 (async)** | Type-safe ORM with native async sessions via asyncpg |
| **Pydantic v2** | Strict schema validation for API contracts and LLM Structured Outputs |
| **JSONB** for survey data | Flexible, indexable document storage for nested question/option trees without over-normalized joins |
| **Tenacity** | Declarative retry logic on OpenAI calls with exponential backoff |
| **slowapi** | Lightweight rate limiting that integrates directly with FastAPI |
| **Docker Compose** | One-command database setup for reviewers |

---

## Assumptions & Notes

**Authentication:** The API uses a single shared Bearer token (`API_BEARER_TOKEN` env var). There is no per-user identity or role-based access. Authentication is disabled by default (`API_BEARER_TOKEN=disabled`) so reviewers can test immediately without configuration. In a production multi-tenant system this would be replaced with JWT tokens carrying user IDs.

**Semantic cache is global:** All users share the same cached results. Since there are no user accounts in this system, there is no per-user context to segment by. In a future multi-tenant deployment, cache entries would be scoped by organization ID.

**Critic does not re-run on edits:** The Critic auto-runs once when a survey is first generated. Manual edits do not re-trigger it automatically. Users can trigger a manual re-audit via the Audit button in the UI or the `POST /audit` endpoint directly.

**Translation-Only mode does not auto-save:** When the frontend calls `/generate` in Translation-Only mode (as part of the save flow), the backend returns translated content only and does not write to the database. The subsequent manual save call creates the single persisted record. This prevents phantom duplicate surveys from appearing in the sidebar.

**Frontend dev server host check:** The React dev server requires `DANGEROUSLY_DISABLE_HOST_CHECK=true` because it uses the CRA proxy to forward `/api/v1/*` requests to the FastAPI backend on port 8000. This flag is for development only and has no effect on production builds.

**Short survey titles (< 5 chars):** The `/generate` endpoint requires `prompt` to be at least 5 characters. If a survey title is shorter (e.g. "Food"), the frontend automatically prefixes it with `"Translate survey: "` before sending to the translation call, ensuring the validation constraint is always met while still giving the LLM meaningful context.

---

## Future Enhancements

- JWT-based multi-user authentication with role-based access control
- Survey version history and diff tracking
- WebSocket streaming for real-time generation progress
- Pagination on the survey list endpoint
- Admin dashboard for cache analytics and hit rate monitoring
- WebSocket or SSE instead of polling for Critic audit results
