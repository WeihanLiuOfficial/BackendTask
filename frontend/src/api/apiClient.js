/**
 * Centralized API client for the Boundary AI Survey backend.
 *
 * All functions use the CRA proxy (package.json "proxy": "http://localhost:8000")
 * so no absolute URLs or CORS config is needed in development.
 *
 * Shape convention:
 *   Backend questions: { id, title: {en, fr}, type, options: [{id, text:{en,fr}}] | null, saved }
 *   Frontend questions (flat): { id, title: string, type, options: [{id, text: string}], saved }
 *
 * Conversion helpers below handle both directions.
 */

const API_BASE = "/api/v1";
const AUTH_TOKEN =
  process.env.REACT_APP_API_TOKEN || "boundary-dev-token-2024";

/** @param {Response} res */
async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function headers() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${AUTH_TOKEN}`,
  };
}

// ─── Shape Converters ───────────────────────────────────────────────────────

/**
 * Convert a backend question (bilingual) to a flat frontend question.
 * @param {object} backendQ
 * @param {'en'|'fr'} lang - which language to surface as the display string
 * @returns {object} flat frontend question
 */
export function backendQuestionToFrontend(backendQ, lang = "en") {
  return {
    id: backendQ.id,
    title: backendQ.title?.[lang] || backendQ.title?.en || "",
    titleBilingual: backendQ.title || { en: "", fr: "" },
    type: backendQ.type,
    saved: backendQ.saved ?? true,
    options: backendQ.options
      ? backendQ.options.map((opt) => ({
          id: opt.id,
          text: opt.text?.[lang] || opt.text?.en || "",
          textBilingual: opt.text || { en: "", fr: "" },
        }))
      : [],
  };
}

/**
 * Convert a flat frontend question back to bilingual backend shape.
 * Merges the active language into the existing bilingual object.
 * @param {object} frontendQ
 * @param {'en'|'fr'} activeLang
 * @returns {object} backend-shaped question
 */
export function frontendQuestionToBackend(frontendQ, activeLang = "en") {
  const existingTitle = frontendQ.titleBilingual || { en: "", fr: "" };
  const title = {
    ...existingTitle,
    [activeLang]: frontendQ.title,
  };

  const options = frontendQ.options
    ? frontendQ.options.map((opt) => {
        const existingText = opt.textBilingual || { en: "", fr: "" };
        return {
          id: opt.id,
          text: {
            ...existingText,
            [activeLang]: opt.text,
          },
        };
      })
    : null;

  return {
    id: frontendQ.id,
    title,
    type: frontendQ.type,
    saved: frontendQ.saved,
    options,
  };
}

/**
 * Detect if a set of questions is missing translations in the inactive language.
 * Used to decide whether to auto-trigger Translation-Only mode on save.
 * @param {object[]} frontendQuestions
 * @param {'en'|'fr'} activeLang
 */
export function needsTranslation(frontendQuestions, activeLang) {
  const otherLang = activeLang === "en" ? "fr" : "en";
  return frontendQuestions.some((q) => {
    const hasOtherTitle = q.titleBilingual?.[otherLang]?.trim();
    return !hasOtherTitle;
  });
}

// ─── API Functions ──────────────────────────────────────────────────────────

/** @returns {Promise<{surveys: object[], total: number}>} */
export async function getSurveys() {
  const res = await fetch(`${API_BASE}/surveys`, { headers: headers() });
  return handleResponse(res);
}

/** @param {string} id @returns {Promise<object>} */
export async function getSurvey(id) {
  const res = await fetch(`${API_BASE}/surveys/${id}`, { headers: headers() });
  return handleResponse(res);
}

/**
 * Create a new survey.
 * @param {{ title:{en,fr}, description:{en,fr}, questions: object[] }} data
 */
export async function createSurvey(data) {
  const res = await fetch(`${API_BASE}/surveys`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/**
 * Update an existing survey.
 * @param {string} id
 * @param {{ title:{en,fr}, description:{en,fr}, questions: object[] }} data
 */
export async function updateSurvey(id, data) {
  const res = await fetch(`${API_BASE}/surveys/${id}`, {
    method: "PUT",
    headers: headers(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/** @param {string} id */
export async function deleteSurvey(id) {
  const res = await fetch(`${API_BASE}/surveys/${id}`, {
    method: "DELETE",
    headers: headers(),
  });
  return handleResponse(res);
}

/**
 * AI generation endpoint.
 * @param {{ prompt: string, question_count?: number, existing_questions?: object[], add_more_questions?: boolean }} data
 */
export async function generateSurvey(data) {
  const res = await fetch(`${API_BASE}/surveys/generate`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/**
 * Trigger manual Critic audit on a saved survey.
 * @param {string} id
 */
export async function auditSurvey(id) {
  const res = await fetch(`${API_BASE}/surveys/${id}/audit`, {
    method: "POST",
    headers: headers(),
  });
  return handleResponse(res);
}
