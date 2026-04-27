# Backend Architecture Specification: Tri-Modal Survey Generation Engine

## 1. Executive Summary

The platform is designed as an ultra-low-latency, AI-native survey orchestration engine. Built entirely on an asynchronous event loop using **FastAPI (Python 3.11)**, the system diverges from standard CRUD monoliths by implementing a native **Semantic Vector Cache** and an **Optimistic Actor-Critic LLM Pipeline**. 

This architecture guarantees sub-second Time-To-First-Byte (TTFB) for users while maintaining rigorous data integrity via strictly typed localized schemas.

---

## 2. Infrastructure & Persistence Layer

### 2.1 Asynchronous Database Connectivity
The application relies on **PostgreSQL 16** via the **`asyncpg`** driver. Unlike traditional threaded execution (e.g., `psycopg2`), `asyncpg` operates entirely on the `asyncio` event loop. This prevents the server from blocking during high-latency network calls (like LLM generation or heavy similarity searches), allowing a single lightweight Uvicorn worker to handle thousands of concurrent generation requests.

### 2.2 Semantic Vector Cache (`pgvector`)
To minimize expensive API calls to OpenAI and drastically reduce generation latency, the system implements a Semantic Cache using the `pgvector` extension.
*   **Vectorization:** User prompts (for zero-to-one generation) are mapped to a 1536-dimensional continuous vector space using OpenAI's `text-embedding-3-small`.
*   **Index Structure:** The `SurveyCache` table utilizes an **HNSW (Hierarchical Navigable Small World)** or **IVFFlat** index on the vector column.
*   **Query Execution:** On inbound generation requests, the backend executes a highly optimized Cosine Distance query (`<=>`). If $1 - \text{cosine\_distance}(A, B) > 0.95$, the system triggers a **Cache Hit**, bypassing the LLM entirely and immediately yielding the stored `JSONB` payload.

### 2.3 Relational & Document Storage Hybrid (`JSONB`)
While surveys, users, and organizational data maintain strict relational normalization (3NF) via **SQLAlchemy 2.0 (Async)**, the actual survey topologies (questions, multi-lingual nested options) are stored in highly optimized **`JSONB`** columns. 
*   **Why `JSONB`?** It enables indexable, binary-parsed document storage. This permits native SQL querying *inside* the survey structure (e.g., filtering all surveys that contain a `npsScore` question) without the severe performance penalty of joining heavily normalized tables for deeply nested, localized choices.

---

## 3. The Tri-Modal Orchestration Engine

The core API endpoint (`POST /api/surveys/generate`) functions as an intelligent router capable of parsing the inbound payload state and selecting one of three execution paths:

### Modality 1: Zero-to-One Synthesis
*   **Trigger:** Inbound payload contains a prompt but `existing_questions` is null.
*   **Execution:** Initiates the semantic cache lookup. On miss, routes to the core LLM generation pipeline to synthesize the entire structure.

### Modality 2: Context-Aware Expansion (Hybrid)
*   **Trigger:** Payload contains a prompt, existing manual questions, and `add_more_questions=true`.
*   **Execution:** Bypasses semantic cache (as context is highly mutated). Injects the existing JSON topology into the LLM system prompt as "locked context." The LLM acts as an extrapolation engine, predicting and appending orthogonal question clusters without mutating the user's manual work.

### Modality 3: Schema Normalization & Localization
*   **Trigger:** Payload contains manual questions but `add_more_questions=false`.
*   **Execution:** Acts purely as a data transformation and translation pipeline. Enforces the `LocalizedText` Pydantic bounds (generating `fr` variants for all `en` inputs) and auto-completes missing options based on the `requested_option_count` heuristic.

---

## 4. Optimistic Actor-Critic Pipeline

Chaining multiple LLM agents synchronously destroys UX due to cumulative token generation latency. We solve this using an **Optimistic Generator + Asynchronous QA** architecture.

### 4.1 The Generator (Synchronous)
1.  **Strict Output Enforcement:** We utilize OpenAI's Native Structured Outputs tightly coupled to our Pydantic v2 schemas. This forces the LLM's probability distribution to only emit tokens that satisfy our JSON schema (including the `en` and `fr` localized dictionaries).
2.  **Optimistic Yield:** Because Structured Outputs mathematically guarantee schema adherence, we optimistically assume qualitative success. The moment the JSON stream completes, the FastAPI endpoint `return`s the HTTP response to the client.

### 4.2 The Critic (Asynchronous Background Task)
1.  **Detached Evaluation:** Immediately upon returning the HTTP response, FastAPI attaches the generated draft to the `BackgroundTasks` queue.
2.  **Qualitative Auditing:** A secondary LLM agent (The Critic) analyzes the draft strictly for bias, survey fatigue (UX), and linguistic naturalness of the French translation. 
3.  **Eventual Consistency:** If the Critic detects a flaw, it applies a patch to the database entity and can optionally push a WebSocket (or SSE) invalidation event to the client to prompt a UI refresh.

---

## 5. Data Validation Boundary

All I/O crossing the API boundary is sanitized via **Pydantic v2**. 

```python
class LocalizedText(BaseModel):
    en: str
    fr: str

class QuestionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: QuestionType
    title: LocalizedText
    options: Optional[List[OptionSchema]] = None
    requested_option_count: Optional[int] = None
```
This declarative approach ensures that the FastAPI application fundamentally cannot process, store, or return structurally invalid data, effectively mitigating prompt injection anomalies that result in malformed JSON.
