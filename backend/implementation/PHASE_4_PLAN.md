# Phase 4: AI Integration — Full Implementation Plan

The core feature: turning a text prompt into a fully structured bilingual survey via OpenAI, with semantic caching, background quality auditing, and all three Tri-Modal generation paths.

---

## User Review Required

### 1. Critic Cost Concern
**The Critic now audits ALL surveys — not just AI-generated ones.** This means `POST /surveys` (manual create), `PUT /surveys/{id}` (manual update), and `POST /surveys/generate` all dispatch the Critic. This adds an OpenAI API call for every manual save/update. **Are you okay with the cost of an extra LLM call on every save?** If cost is a concern, we can limit the Critic to AI-generated surveys only and add a manual "Audit" button in the frontend later.

### 2. Frontend Changes Are NOT In This Phase
Phase 4 is backend-only. The quality issues will be available in the API response, but frontend rendering (red sidebar, issue indicators) will be Phase 5. Confirm this is acceptable.

---

## Proposed Changes

### Schema Layer

#### [MODIFY] survey.py (backend/app/schemas/survey.py)

Add quality issue schemas and update request/response models:

```python
# New schemas
class QualityIssue(BaseModel):
    """A single quality concern found by the Critic agent."""
    issue_type: Literal["question_level", "survey_level"]
    question_id: Optional[str] = None  # null for survey-level issues
    severity: Literal["info", "warning", "critical"]
    message_en: str
    message_fr: str

# Update GenerateSurveyRequest
question_count: Optional[int] = Field(
    default=None, ge=1, le=50,
    description="Desired number of questions. If null, the AI decides based on the topic.",
)

# Update SurveyResponse — add quality_issues
quality_issues: Optional[List[QualityIssue]] = Field(
    default=None,
    description="Quality concerns identified by the Critic agent (populated asynchronously).",
)

# Update SurveyListItem — add has_quality_issues flag
has_quality_issues: bool = Field(
    default=False,
    description="Whether the Critic has flagged any issues. Used to mark surveys red in the sidebar.",
)
```

---

### Model Layer

#### [MODIFY] survey.py (backend/app/models/survey.py)

Add `quality_issues` JSONB column to the Survey model:

```python
quality_issues = Column(
    JSONB,
    nullable=True,
    doc="Quality issues found by the Critic agent. Null means not yet audited.",
)
```

#### [NEW] Alembic migration — `add_quality_issues_column`

Adds the `quality_issues` JSONB column. As always, manually inspect for false-positive HNSW index drops.

---

### Service Layer — Semantic Cache

#### [MODIFY] semantic_cache.py (backend/app/services/cache/semantic_cache.py)

Implement all three functions:

1. **`embed_prompt()`** — calls `openai.embeddings.create(model="text-embedding-3-small", input=prompt)`, returns the 1536-dim vector
2. **`find_similar_survey()`** — executes:
   ```sql
   SELECT *, 1 - (prompt_embedding <=> :vector) AS similarity
   FROM survey_cache
   WHERE 1 - (prompt_embedding <=> :vector) > :threshold
   ORDER BY similarity DESC LIMIT 1
   ```
3. **`store_in_cache()`** — inserts a new `SurveyCache` row with prompt, embedding, and result JSONB

**Cache scope:** Global (no user accounts). Documented in README.

---

### Service Layer — Generator Agent

#### [MODIFY] prompts.py (backend/app/services/ai/prompts.py)

Three system prompts per modality:

- **Zero-to-One:** "You are a professional survey designer. Generate a complete bilingual (EN/FR) survey for the following topic. Use diverse question types: singleChoice, multipleChoice, openQuestion, shortAnswer, scale, npsScore..."
- **Hybrid Expansion:** "You are enhancing an existing survey. The user has provided existing questions (DO NOT modify or remove them). Generate additional questions that complement them..."
- **Translation-Only:** "Translate and format the following questions into a complete bilingual survey structure without adding or removing any questions..."

User prompt includes: the raw prompt text, optional question_count hint, optional existing questions serialized as JSON.

#### [MODIFY] generator.py (backend/app/services/ai/generator.py)

Implement `generate_survey_with_llm()`:
1. Build system + user prompts via `prompts.py`
2. Call `openai_client.beta.chat.completions.parse(response_format=SurveySchema)`
3. Return the parsed `SurveySchema` — validation is automatic via Structured Outputs
4. Retry decorator: 3 attempts with exponential backoff

---

### Service Layer — Critic Agent

#### [MODIFY] critic.py (backend/app/services/ai/critic.py)

Implement `run_critic_audit()`:
1. Creates its own async DB session (runs outside request lifecycle)
2. Builds a critic prompt that instructs the LLM to evaluate:
   - **Question-level:** bias, leading phrasing, ambiguity, poor French translation
   - **Survey-level:** question type distribution fatigue, logical ordering, missing coverage
3. Calls OpenAI with a `List[QualityIssue]` response format
4. If issues found → writes `quality_issues` JSONB to the survey row
5. If no issues → writes `[]` (empty array signals "audited, all clean")

**Trigger points:** Called from:
- `generation_service.generate_survey()` — on cache misses
- `survey_service.save_survey()` — on manual creates
- `survey_service.update_survey()` — on manual updates

---

### Service Layer — Generation Orchestrator

#### [MODIFY] generation_service.py (backend/app/services/generation_service.py)

Already scaffolded. Minor updates:
- Pass `question_count` from request to generator prompt
- Only cache Zero-to-One results (Hybrid/Translation are context-dependent)

---

### API Layer

#### [MODIFY] surveys.py (backend/app/api/v1/surveys.py)

- Wire `BackgroundTasks` into `create_survey` and `update_survey` endpoints for Critic dispatch
- The `generate_survey` endpoint already delegates to `generation_service`

---

### Service Layer — Survey CRUD

#### [MODIFY] survey_service.py (backend/app/services/survey_service.py)

- Update `_orm_to_response()` to include `quality_issues` from the ORM model
- Update `SurveyListItem` mapping to include `has_quality_issues` flag
- `save_survey()` and `update_survey()` accept optional `BackgroundTasks` param for Critic dispatch

---

### Documentation

#### [MODIFY] README.md

- Document global cache scope rationale
- Document Critic behavior on manual vs AI-generated surveys
- Update endpoint table with generation details

---

### Rate Limiter

#### [MODIFY] surveys.py (backend/app/api/v1/surveys.py)

Apply `@limiter.limit(settings.RATE_LIMIT)` decorator to the `/generate` endpoint only.

---

## Execution Order

1. Schema changes (`QualityIssue`, `question_count`, response updates)
2. Model + migration (`quality_issues` JSONB column)
3. Semantic cache implementation
4. Prompt engineering (`prompts.py`)
5. Generator implementation (`generator.py`)
6. Critic implementation (`critic.py`)
7. Wire Critic into CRUD endpoints + generation_service
8. Update `_orm_to_response` and list mapping
9. Rate limiter on `/generate`
10. README updates
11. Test full flow end-to-end

## Verification Plan

### Automated Tests
```bash
# 1. Generate a survey (Zero-to-One) — should return valid survey with cache_hit=false
curl -X POST /api/v1/surveys/generate -d '{"prompt": "Customer satisfaction for an online store"}'

# 2. Same prompt again — should return cache_hit=true (no LLM call)

# 3. Verify quality_issues populated after a few seconds (background Critic)
curl -X GET /api/v1/surveys/{id}  # quality_issues should be non-null

# 4. Create a manual survey — verify Critic runs
curl -X POST /api/v1/surveys -d '{...}'

# 5. Rate limit test — send 11 requests in 1 minute, 11th should get 429
```

### Manual Verification
- Check Swagger UI for correct OpenAPI schema rendering
- Verify HNSW index not dropped in migration
- Check server logs for Critic background task completion
