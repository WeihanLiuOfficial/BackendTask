# Backend Task

This task is designed to evaluate your backend skills, API design, code quality, architecture, and creativity. The goal is to augment the provided isolated frontend page with a fully working survey-generation feature.

To do so you are asked to create an AI-powered survey generator that transforms a user’s brief description into a fully structured questionnaire, covering diverse question types (multiple-choice, ratings, open-text, etc.) tailored to their needs.

## Description

You have been given an isolated version of one page of our frontend (React + TypeScript): [https://github.com/BoundaryAIRecruitment/BackendTask](https://github.com/BoundaryAIRecruitment/BackendTask)

Your job is to:

* **Add a “Generate Survey” button to the page:**

  * When clicked, it should prompt the user to enter a short survey description (e.g. “Customer satisfaction for an online store”).
  * Once submitted, the frontend should call your new backend endpoint.

* **Implement the backend (using Flask or FastAPI, your choice):**

  * **Route(s):**

    * A POST endpoint (e.g. `/api/surveys/generate`) that accepts the user’s description.
  * **Logic & Integration:**

    * Use the OpenAI API, or another LLM of your choice to generate a structured survey.
    * It is recommended that the output be JSON-structured (e.g. `{ "title": "...", "questions": [ { "type": "...", "text": "..." }, … ] }`).
  * **Storage:** save generated surveys for repeated prompts.

    * Save the input and output in a PostGreSQL database; if an input is the same, you should fetch it instead of generate it.
  * **Auto-fill:**

    * Return the generated JSON so the frontend can render the new survey form automatically.

## Tech Stack

* **Language:** Python (3.11)
* **Framework:** Flask or FastAPI
* **AI Integration:** OpenAI API (or equivalent LLM)

## What We are Evaluating

* **Architecture & Design**

  * Logical separation of concerns (routes, services, models), clear dependency injection or config management.
* **Code Quality**

  * Clean, modular, well-documented code following best practices and style guides.
* **API Design**

  * RESTful principles, clear request/response schemas, proper status codes and error messages.
* **Integration & Robustness**

  * Correct handling of API keys, timeouts, retries, input validation, and error cases.
* **Performance & Security**

  * Efficient request handling, minimal cold-start overhead, sanitization of inputs.
* **Documentation**

  * Clear README explaining setup, env vars, how to run, and any design decisions.

## Submission

Provide one of the following:

* A GitHub repository (with public or private access) or a ZIP archive containing your code.
* (Optional) A deployed version of your backend (e.g. on Heroku, Vercel Functions, or similar) with URL.

Include a brief README that covers:

* Tech choices (why Flask vs. FastAPI, any libraries you picked)
* Setup & Run instructions (install, env vars, start server)
* Areas of focus (What did you implement that other candidates might not have?)

## Bonus Points

* **Dockerization:** supply a Dockerfile and easy docker-compose setup.
* **Testing:** Unit and/or integration tests covering core functionality.
* **Authentication:** simple token check on your API.
* **Rate limiting:** prevent abuse of the generation endpoint.
* **Security:**

Feel free to innovate beyond the spec. If you see an opportunity to improve UX or backend architecture, show us. Good luck!

---
---

# Implementation — Boundary AI Survey Generation Backend

An AI-powered survey generation engine built with **FastAPI**, **PostgreSQL 16 (pgvector)**, and **OpenAI GPT-4o-mini**. Implements a Tri-Modal generation pipeline with semantic caching, an Optimistic Actor-Critic AI pattern, and full bilingual (EN/FR) support.

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd BackendTask

# 2. Copy environment template
cp backend/.env.example backend/.env
# Edit backend/.env and add your OPENAI_API_KEY

# 3. Start the database
docker-compose up -d db

# 4. Set up Python environment
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

# 5. Run database migrations
# Windows PowerShell:
$env:PYTHONPATH = "."; .venv/Scripts/alembic upgrade head
# macOS/Linux:
# PYTHONPATH=. alembic upgrade head

# 6. Start the API server
$env:PYTHONPATH = "."; .venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 7. Start the frontend (in a separate terminal)
cd frontend && npm install && npm start
```

**Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://boundary:boundary_secret@localhost:5432/boundary_surveys` | Async PostgreSQL connection string |
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for survey generation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model for prompt embeddings |
| `API_BEARER_TOKEN` | `disabled` | Set to `disabled` for open access; set to any string to enable Bearer auth |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `SIMILARITY_THRESHOLD` | `0.95` | Cosine similarity threshold for semantic cache hits |
| `RATE_LIMIT` | `10/minute` | Rate limit for the generation endpoint |
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
| `POST` | `/api/v1/surveys/generate` | AI-powered survey generation |

---

## Authentication

Authentication uses **Bearer token** via the `Authorization` header.

**Default behavior:** Authentication is **disabled** out of the box (`API_BEARER_TOKEN=disabled` in `.env.example`). This ensures zero-friction setup for reviewers — the API works immediately after cloning.

**To enable authentication:** Set `API_BEARER_TOKEN` to any secret string in your `.env` file. All endpoints (except `/health`) will then require:

```
Authorization: Bearer your-secret-string
```

> **Note on authentication scope:** This implementation uses a single shared token for all users. There is no concept of per-user identity or role-based access control. In a production multi-tenant system, this would be replaced with JWT tokens carrying user IDs and scoped permissions. The current design is intentionally simple to match the scope of the task while demonstrating the auth pattern.

---

## Semantic Cache (pgvector + HNSW)

To avoid redundant OpenAI API calls, the system implements a **semantic similarity cache** using PostgreSQL's `pgvector` extension.

**How it works:**
1. When a user submits a generation prompt, the prompt is converted to a 1536-dimensional vector using OpenAI's `text-embedding-3-small` model.
2. The vector is compared against all cached prompt vectors using cosine similarity.
3. If a cached prompt has similarity > 0.95 (configurable via `SIMILARITY_THRESHOLD`), the cached result is returned immediately — no LLM call is made.
4. On a cache miss, the LLM generates the survey and the result is stored in the cache for future lookups.

**Index configuration:** The `prompt_embedding` column uses an **HNSW (Hierarchical Navigable Small World)** index with `vector_cosine_ops` for fast approximate nearest-neighbor search. This reduces similarity lookups from O(n) full table scans to O(log n) graph traversals.

The HNSW index uses default parameters:
- **`m = 16`** — Maximum number of connections per node in the graph. Higher values increase recall accuracy but consume more memory and slow down insertions.
- **`ef_construction = 64`** — Size of the dynamic candidate list during index construction. Higher values produce a more accurate index at the cost of slower build times.

These defaults are well-suited for up to ~100,000 cached vectors. For larger deployments, tuning `m` and `ef_construction` would be recommended based on recall/latency benchmarks.

---

## Architecture Highlights

- **Async everything:** FastAPI + SQLAlchemy 2.0 async + asyncpg. No thread blocking.
- **Optimistic Actor-Critic pattern:** Agent 1 (Generator) returns immediately; Agent 2 (Critic) audits quality in the background via `BackgroundTasks`.
- **Tri-Modal generation:** Zero-to-One (full synthesis), Hybrid (context-aware expansion), and Translation/Formatting modes.
- **Soft delete:** Surveys are never permanently removed. They are flagged as deleted and can be restored.
- **Bilingual support:** All text fields support English and French (`LocalizedText` schema).
- **Structured Outputs:** OpenAI responses are constrained to a strict JSON schema for reliable parsing.

---

## Project Structure

```
backend/
├── app/
│   ├── api/v1/           # Route handlers (health, surveys)
│   ├── middleware/        # Auth middleware
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # Business logic (survey CRUD, AI agents)
│   │   └── ai/            # Generator, Critic, Semantic Cache
│   ├── config.py          # Pydantic settings (env var validation)
│   ├── dependencies.py    # FastAPI dependency injection
│   └── main.py            # Application factory + lifespan
├── alembic/               # Database migrations
├── implementation/        # Phase-by-phase implementation logs
├── tests/                 # Test stubs
├── requirements.txt
└── Dockerfile
```

---

## Tech Choices

| Choice | Why |
|---|---|
| **FastAPI** over Flask | Native async support, automatic OpenAPI docs, Pydantic integration, dependency injection |
| **PostgreSQL 16 + pgvector** | Semantic caching with vector similarity — eliminates the need for a separate vector database (Pinecone, Weaviate) |
| **SQLAlchemy 2.0 (Async)** | Type-safe ORM with native async session support via asyncpg |
| **Pydantic v2** | Strict schema validation for both API contracts and LLM output enforcement |
| **JSONB** for survey data | Enables flexible, indexable document storage for deeply nested question/option trees without over-normalized joins |
| **Docker Compose** | One-command infrastructure setup for the reviewer |

---

## Future Enhancements

- JWT-based multi-user authentication with role-based access control
- Survey version history and diff tracking
- WebSocket streaming for real-time generation progress
- Pagination on the survey list endpoint
- Admin dashboard for cache analytics and hit rate monitoring
