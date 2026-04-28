# Phase 5 — Full-Stack Frontend Integration

**Status:** ✅ Complete  
**Date:** 2026-04-28

---

## What Was Implemented

### 1. Dependency & Proxy Setup
- Installed `react-router-dom` and `react-hot-toast` (already present in node_modules).
- Added `"proxy": "http://localhost:8000"` to `frontend/package.json` so all `fetch('/api/v1/...')` calls forward transparently to FastAPI without CORS overhead.
- Dev server must be started with `DANGEROUSLY_DISABLE_HOST_CHECK=true` due to a known CRA bug with proxy + allowedHosts.

### 2. API Client (`src/api/apiClient.js`) — NEW FILE
- Centralized all backend requests in one module.
- Bidirectional shape converters: `backendQuestionToFrontend()` and `frontendQuestionToBackend()` handle the `{en, fr}` bilingual object ↔ flat UI string conversion.
- `needsTranslation()` helper detects whether French content is missing.
- Typed wrappers for all endpoints: `getSurveys`, `getSurvey`, `createSurvey`, `updateSurvey`, `deleteSurvey`, `generateSurvey`, `auditSurvey`.
- `handleResponse()` extracts error detail from the FastAPI error body for clean toast messages.

### 3. Router Setup (`src/App.js`) — REWRITTEN
- Bootstrapped `BrowserRouter` wrapping the entire app.
- Routes: `/` → redirect, `/surveys` (landing), `/surveys/new`, `/surveys/:id`.
- `CreateSurveyProvider` wraps all routes so context is available app-wide.
- Global `<Toaster>` registered once at the top level.

### 4. `CreateSurveyProvider.jsx` — FULL REWRITE
- Replaced all mock state with real API calls.
- **Bilingual state**: `surveyTitleEn/Fr`, `surveyDescEn/Fr` stored separately; `activeLang` determines which one surfaces to UI.
- **One-shot auto-translation**: `_translationNeeded()` checks if French is empty; if so, fires Translation-Only LLM call on first save, then never again once `fr` fields are populated.
- **AI generation** (`handleGenerate`): calls `/api/v1/surveys/generate`, populates all state, navigates to new survey URL, shows cache-hit/new toast.
- **Manual Critic audit** (`handleAudit`): calls `/api/v1/surveys/{id}/audit`, then polls `GET /surveys/{id}` every 3s for up to 30s waiting for `quality_issues` to be populated.
- **Quality issue mapping**: `qualityIssueMap` (question_id → issues[]) and `surveyLevelIssues` derived from Critic response.
- **Bug fixed**: sidebar refresh callback stored in a `useRef` (not `useState`) to avoid React's updater-function trap where `setState(() => fn)` calls `fn(prevState)` instead of storing `fn`.

### 5. `Sidebar.jsx` — REWRITTEN
- Fetches survey list from `GET /api/v1/surveys` on mount.
- Registers `onSurveyListChangedRef.current = fetchSurveys` via context so Save/Generate actions can trigger a sidebar refresh.
- Red left-border + red dot indicator on any survey with `has_quality_issues: true`.
- Active survey highlighted.
- Animated entry/exit for survey list items.
- "✨ Generate with AI" and "+ New Survey" buttons at top.

### 6. New Components
| File | Purpose |
|---|---|
| `src/api/apiClient.js` | Centralized typed API client |
| `src/pages/SurveyListPage.jsx` | Landing page when no survey is selected |
| `src/pages/CreateSurveyPage.jsx` | Reads `:id` param, calls `loadSurvey()` or `resetSurvey()` |
| `src/component/LanguageToggle.jsx` | EN/FR pill toggle, reads `activeLang` from context |
| `src/component/AIGenerateModal.jsx` | Modal with prompt, count, keep-existing toggle |
| `src/component/QualityIssueBox.jsx` | Animated inline warning box below flagged questions |

### 7. `CreateSurvey.jsx` — REWRITTEN
- Accepts `autoOpenAI` prop (from `?ai=true` URL param) to auto-open the AI modal.
- Top action bar: Language toggle, Audit button (only shown when survey is saved), Save button.
- Survey-level issues banner above the question list.
- "Add Question" + "✨ Generate" side-by-side bottom buttons.

### 8. `QuestionItem.jsx` — REWRITTEN
- Fragment-wrapped Draggable render prop to allow `QualityIssueBox` as a JSX sibling.
- Question card turns red-bordered (`border-red-400`) when Critic has flagged it.
- `QualityIssueBox` rendered directly below each question card.

---

## Bugs Hit & Fixes

### Bug 1: JSX Syntax Error in QuestionItem
- **Symptom:** Build failed with "Unexpected token, expected ','".
- **Root cause:** `QualityIssueBox` placed as a sibling of the Draggable render prop's root `<div>`, which JSX disallows (single root element rule).
- **Fix:** Wrapped both in `<>...</>` fragment.

### Bug 2: React Updater-Function Trap
- **Symptom:** Sidebar refresh callback was being called immediately on registration instead of being stored.
- **Root cause:** `setState(() => fn)` — React treats any function passed to a setter as `(prevState) => newState`. Calling `setOnSurveyListChanged(() => fetchSurveys)` invoked `fetchSurveys(prevState)` immediately.
- **Fix:** Replaced state with a `useRef`; the context exposes `setOnSurveyListChanged: (fn) => { onSurveyListChangedRef.current = fn; }`.

### Bug 3: CRA Dev Server allowedHosts error
- **Symptom:** Dev server crashed with "options.allowedHosts[0] should be a non-empty string" after adding `proxy` to `package.json`.
- **Root cause:** Known bug in `react-scripts@5.x` where proxy + host validation conflict.
- **Fix:** Start dev server with `DANGEROUSLY_DISABLE_HOST_CHECK=true npm start`.

---

## Known Technical Debt

1. **`CreateSurveyContent.jsx` and `CreateSurveySidebar.jsx`**: Pre-existing files with unused vars (lint warnings). These are unused stubs from the original codebase. Safe to delete in cleanup pass.
2. **`handleDeleteOption` in `QuestionItem`**: Destructured from context but not wired to a UI button in the current question item. Wire when per-option delete UI is needed.
3. **Auth token**: `REACT_APP_API_TOKEN=boundary-dev-token-2024` is hardcoded in `apiClient.js`. For production, this should come from an environment variable and the backend should validate it properly.
4. **No optimistic UI on Save**: The sidebar doesn't show the new/updated survey until the API responds and the refresh fires. A future pass could add an optimistic insertion.
5. **Poll timeout**: The 30s audit poll is a pragmatic solution. Consider WebSockets or Server-Sent Events for production if audit latency becomes an issue.

---

## Verified Final State

```
npm run build → exit code 0 (warnings only, no errors)
GET http://localhost:3000 → 200 OK
Backend API shape confirmed: SurveyListItem.title = LocalizedText(en, fr) ✓
Backend SurveyListItem.has_quality_issues field confirmed ✓
Backend POST /{survey_id}/audit endpoint confirmed ✓
```

---

## Command Reference

```bash
# Start frontend dev server (proxy fix required)
cd frontend
$env:DANGEROUSLY_DISABLE_HOST_CHECK = "true"; npm start

# Start backend (separate terminal)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Build production bundle
cd frontend
npm run build
```
