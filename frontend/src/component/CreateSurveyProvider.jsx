import React, { createContext, useContext, useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import {
  createSurvey,
  updateSurvey,
  getSurvey,
  generateSurvey,
  auditSurvey,
  backendQuestionToFrontend,
  frontendQuestionToBackend,
  needsTranslation as checkNeedsTranslation,
} from "../api/apiClient";

const CreateSurveyContext = createContext();

export const CreateSurveyProvider = ({ children }) => {
  const navigate = useNavigate();

  // ── Survey Identity ────────────────────────────────
  const [surveyId, setSurveyId] = useState(null);

  // ── Survey Fields ──────────────────────────────────
  // We store bilingual title/description as separate en/fr fields for simplicity.
  // activeLang controls which one the user edits.
  const [surveyTitleEn, setSurveyTitleEn] = useState("");
  const [surveyTitleFr, setSurveyTitleFr] = useState("");
  const [surveyDescEn, setSurveyDescEn] = useState("");
  const [surveyDescFr, setSurveyDescFr] = useState("");

  // ── Language ───────────────────────────────────────
  const [activeLang, setActiveLang] = useState("en");

  // ── Questions (flat frontend shape) ───────────────
  const [questions, setQuestions] = useState([]);

  // ── Quality Issues ─────────────────────────────────
  // Map: question_id → [QualityIssue]
  const [qualityIssueMap, setQualityIssueMap] = useState({});
  // survey-level issues (question_id is null)
  const [surveyLevelIssues, setSurveyLevelIssues] = useState([]);

  // ── Loading States ─────────────────────────────────
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAuditing, setIsAuditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // ── Misc ───────────────────────────────────────────
  const [isAddingOption, setIsAddingOption] = useState(false);
  const defaultQuestionType = "shortAnswer";

  // Sidebar refresh ref + stable setter (ref avoids the React updater-function
  // trap; useCallback ensures the setter reference is stable across renders)
  const onSurveyListChangedRef = useRef(null);
  const setOnSurveyListChanged = useCallback((fn) => {
    onSurveyListChangedRef.current = fn;
  }, []);

  // Audit polling ref
  const pollRef = useRef(null);

  // ── Computed helpers ───────────────────────────────
  const surveyTitle = activeLang === "en" ? surveyTitleEn : surveyTitleFr;
  const surveyDescription = activeLang === "en" ? surveyDescEn : surveyDescFr;

  const setSurveyTitle = (val) => {
    if (activeLang === "en") setSurveyTitleEn(val);
    else setSurveyTitleFr(val);
  };

  const setSurveyDescription = (val) => {
    if (activeLang === "en") setSurveyDescEn(val);
    else setSurveyDescFr(val);
  };

  // ── Sync question display strings when language changes ──────────────────
  // Questions are stored with a flat `title` string (what the UI renders) and
  // a `titleBilingual` object {en, fr} (the source of truth). When activeLang
  // changes we re-derive the flat string from the bilingual object so the UI
  // reflects the correct language immediately — without a page refresh.
  useEffect(() => {
    setQuestions((prev) =>
      prev.map((q) => ({
        ...q,
        title: q.titleBilingual?.[activeLang] ?? q.titleBilingual?.en ?? q.title,
        options: (q.options || []).map((opt) => ({
          ...opt,
          text: opt.textBilingual?.[activeLang] ?? opt.textBilingual?.en ?? opt.text,
        })),
      }))
    );
  }, [activeLang]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load Survey ────────────────────────────────────
  const loadSurvey = useCallback(async (id) => {
    setIsLoading(true);
    try {
      const data = await getSurvey(id);
      setSurveyId(id);
      setSurveyTitleEn(data.survey.title?.en || "");
      setSurveyTitleFr(data.survey.title?.fr || "");
      setSurveyDescEn(data.survey.description?.en || "");
      setSurveyDescFr(data.survey.description?.fr || "");

      const flatQuestions = (data.survey.questions || []).map((q) =>
        backendQuestionToFrontend(q, activeLang)
      );
      setQuestions(flatQuestions);

      // Load quality issues
      _applyQualityIssues(data.quality_issues || []);
    } catch (err) {
      toast.error(`Failed to load survey: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [activeLang]);

  const _applyQualityIssues = (issues) => {
    const map = {};
    const surveyLevel = [];
    for (const issue of issues) {
      if (issue.question_id) {
        if (!map[issue.question_id]) map[issue.question_id] = [];
        map[issue.question_id].push(issue);
      } else {
        surveyLevel.push(issue);
      }
    }
    setQualityIssueMap(map);
    setSurveyLevelIssues(surveyLevel);
  };

  // ── Reset (for "New Survey") ───────────────────────
  const resetSurvey = useCallback(() => {
    setSurveyId(null);
    setSurveyTitleEn("");
    setSurveyTitleFr("");
    setSurveyDescEn("");
    setSurveyDescFr("");
    setQuestions([]);
    setQualityIssueMap({});
    setSurveyLevelIssues([]);
  }, []);

  // ── Build backend payload ──────────────────────────
  // Accepts optional overrides so the caller can pass freshly-translated
  // values instead of relying on stale React state after setState calls.
  const _buildPayload = ({
    titleEn = surveyTitleEn,
    titleFr = surveyTitleFr,
    descEn  = surveyDescEn,
    descFr  = surveyDescFr,
    qs      = questions,
  } = {}) => {
    const backendQuestions = qs.map((q) =>
      frontendQuestionToBackend(q, activeLang)
    );
    return {
      title:       { en: titleEn, fr: titleFr },
      description: { en: descEn,  fr: descFr  },
      is_ordered: true,
      questions: backendQuestions,
    };
  };

  // ── Check if translation is needed (once) ──────────
  const _translationNeeded = () => {
    const otherLangEmpty = activeLang === "en"
      ? (!surveyTitleFr.trim() || !surveyDescFr.trim())
      : (!surveyTitleEn.trim() || !surveyDescEn.trim());
    const questionsMissing = checkNeedsTranslation(questions, activeLang);
    return otherLangEmpty || questionsMissing;
  };

  // ── Auto-translate (once, before first save) ───────
  // Returns the merged bilingual snapshot so the caller can build the
  // save payload immediately — avoids the React stale-state trap where
  // setState is async and _buildPayload would read old values.
  const _autoTranslate = async () => {
    const backendQuestions = questions.map((q) =>
      frontendQuestionToBackend(q, activeLang)
    );
    const surveyTopic = surveyTitleEn || surveyTitleFr || "Survey";
    const translationPrompt =
      surveyTopic.length >= 5
        ? surveyTopic
        : `Translate survey: ${surveyTopic}`;

    const genPayload = {
      prompt: translationPrompt,
      existing_questions: backendQuestions,
      add_more_questions: false, // Translation-Only mode
    };
    const result = await generateSurvey(genPayload);
    const translated = result.survey;

    // Build merged bilingual snapshot
    const mergedTitleEn  = translated.title?.en       || surveyTitleEn;
    const mergedTitleFr  = translated.title?.fr       || surveyTitleFr;
    const mergedDescEn   = translated.description?.en || surveyDescEn;
    const mergedDescFr   = translated.description?.fr || surveyDescFr;
    const translatedQ    = translated.questions || [];

    const mergedQuestions = questions.map((q, i) => {
      const tq = translatedQ[i];
      if (!tq) return q;
      return {
        ...q,
        titleBilingual: tq.title,
        options: (q.options || []).map((opt, oi) => ({
          ...opt,
          textBilingual: tq.options?.[oi]?.text || opt.textBilingual,
        })),
      };
    });

    // Update state for future renders (these are async — that's fine)
    setSurveyTitleEn(mergedTitleEn);
    setSurveyTitleFr(mergedTitleFr);
    setSurveyDescEn(mergedDescEn);
    setSurveyDescFr(mergedDescFr);
    setQuestions(mergedQuestions);

    // Return synchronously-available merged data for the caller
    return { mergedTitleEn, mergedTitleFr, mergedDescEn, mergedDescFr, mergedQuestions };
  };

  // ── Save Survey (explicit button) ──────────────────
  const handleSaveSurvey = async () => {
    if (isSaving) return;
    if (!surveyTitleEn.trim() && !surveyTitleFr.trim()) {
      toast.error("Please enter a survey title before saving.");
      return;
    }

    setIsSaving(true);
    try {
      // Auto-translate ONCE if the other language is missing.
      // Use the RETURNED merged data directly — do NOT read from state,
      // which won't have updated yet (React setState is asynchronous).
      let payloadOverrides = {};
      // Only auto-translate when there are questions to translate.
      // If questions is empty, existing_questions=[] is sent to the backend,
      // which deterministically triggers zero_to_one mode (not translation_only)
      // and auto-saves a phantom AI-generated survey as a duplicate.
      if (questions.length > 0 && _translationNeeded()) {
        toast.loading("Translating to French…", { id: "translating" });
        const { mergedTitleEn, mergedTitleFr, mergedDescEn, mergedDescFr, mergedQuestions } =
          await _autoTranslate();
        toast.dismiss("translating");
        payloadOverrides = {
          titleEn: mergedTitleEn,
          titleFr: mergedTitleFr,
          descEn:  mergedDescEn,
          descFr:  mergedDescFr,
          qs:      mergedQuestions,
        };
      }

      const payload = _buildPayload(payloadOverrides);

      let saved;
      if (surveyId) {
        saved = await updateSurvey(surveyId, payload);
        // Clear stale audit results — the user just edited the survey so
        // any previous Critic findings are no longer valid. This removes
        // the issue badges from the editor and the red dot from the sidebar.
        setQualityIssueMap({});
        setSurveyLevelIssues([]);
        toast.success("Survey updated.");
      } else {
        saved = await createSurvey(payload);
        setSurveyId(saved.id);
        navigate(`/surveys/${saved.id}`, { replace: true, state: { skipLoad: true } });
        toast.success("Survey saved.");
      }

      onSurveyListChangedRef.current?.();
    } catch (err) {
      toast.error(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // ── AI Generate ─────────────────────────────────────
  const handleGenerate = async (prompt, questionCount, addMore) => {
    setIsGenerating(true);
    try {
      const backendQuestions = addMore
        ? questions.map((q) => frontendQuestionToBackend(q, activeLang))
        : [];

      const payload = {
        prompt,
        ...(questionCount && { question_count: questionCount }),
        ...(backendQuestions.length > 0 && {
          existing_questions: backendQuestions,
          add_more_questions: true,
        }),
      };

      const result = await generateSurvey(payload);
      const generated = result.survey;

      setSurveyId(result.id);
      setSurveyTitleEn(generated.title?.en || "");
      setSurveyTitleFr(generated.title?.fr || "");
      setSurveyDescEn(generated.description?.en || "");
      setSurveyDescFr(generated.description?.fr || "");

      const flatQ = (generated.questions || []).map((q) =>
        backendQuestionToFrontend(q, activeLang)
      );
      setQuestions(flatQ);
      setQualityIssueMap({});
      setSurveyLevelIssues([]);

      navigate(`/surveys/${result.id}`, { replace: true, state: { skipLoad: true } });
      onSurveyListChangedRef.current?.();
      toast.success(`Survey generated (${result.cache_hit ? "from cache" : "new"})!`);

      return result;
    } catch (err) {
      if (err.status === 429) {
        toast.error("Rate limit reached. Please wait a minute and try again.");
      } else {
        toast.error(`Generation failed: ${err.message}`);
      }
      throw err;
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Manual Audit ─────────────────────────────────────
  const handleAudit = async () => {
    if (!surveyId) {
      toast.error("Please save the survey before auditing.");
      return;
    }
    if (isAuditing) return;

    setIsAuditing(true);
    toast.loading("Audit started — checking quality…", { id: "auditing" });

    try {
      await auditSurvey(surveyId);

      // Poll every 3s for up to 30s
      let attempts = 0;
      const maxAttempts = 10;

      clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        attempts++;
        try {
          const data = await getSurvey(surveyId);
          if (data.quality_issues !== null && data.quality_issues !== undefined) {
            clearInterval(pollRef.current);
            _applyQualityIssues(data.quality_issues);
            const issueCount = data.quality_issues.length;
            toast.dismiss("auditing");
            if (issueCount === 0) {
              toast.success("Audit complete — no issues found! ✅");
            } else {
              toast(`Audit complete — ${issueCount} issue${issueCount > 1 ? "s" : ""} found.`, {
                icon: "⚠️",
              });
            }
            setIsAuditing(false);
          }
        } catch (_) {}

        if (attempts >= maxAttempts) {
          clearInterval(pollRef.current);
          toast.dismiss("auditing");
          toast.error("Audit timed out. Try again shortly.");
          setIsAuditing(false);
        }
      }, 3000);
    } catch (err) {
      toast.dismiss("auditing");
      toast.error(`Audit failed: ${err.message}`);
      setIsAuditing(false);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  // ── Question Mutations ─────────────────────────────
  const addNewQuestion = (type = defaultQuestionType) => {
    const newQ = {
      id: `local-${Date.now()}-${Math.random()}`,
      type,
      title: "",
      titleBilingual: { en: "", fr: "" },
      saved: false,
      options:
        type === "multipleChoice" || type === "singleChoice"
          ? [
              { id: crypto.randomUUID(), text: "", textBilingual: { en: "", fr: "" } },
              { id: crypto.randomUUID(), text: "", textBilingual: { en: "", fr: "" } },
            ]
          : [],
    };
    setQuestions((prev) => [...prev, newQ]);
  };

  const handleDeleteQuestion = (index) =>
    setQuestions((prev) => prev.filter((_, i) => i !== index));

  const handleAddOption = useCallback(
    (questionIndex) => {
      if (isAddingOption) return;
      setIsAddingOption(true);
      setQuestions((prev) => {
        const next = [...prev];
        if (!next[questionIndex].options) next[questionIndex].options = [];
        next[questionIndex].options.push({
          id: `opt-${Date.now()}-${Math.random()}`,
          text: "",
          textBilingual: { en: "", fr: "" },
        });
        setTimeout(() => setIsAddingOption(false), 0);
        return next;
      });
    },
    [isAddingOption]
  );

  const handleTitleChange = (questionIndex, title) =>
    setQuestions((prev) => {
      const next = [...prev];
      next[questionIndex] = {
        ...next[questionIndex],
        title,
        titleBilingual: {
          ...next[questionIndex].titleBilingual,
          [activeLang]: title,
        },
      };
      return next;
    });

  const handleQuestionTypeChange = (questionIndex, type) =>
    setQuestions((prev) => {
      const next = [...prev];
      next[questionIndex] = { ...next[questionIndex], type };
      if (type === "multipleChoice" || type === "singleChoice") {
        if (!next[questionIndex].options || next[questionIndex].options.length < 2) {
          next[questionIndex].options = [
            { id: crypto.randomUUID(), text: "", textBilingual: { en: "", fr: "" } },
            { id: crypto.randomUUID(), text: "", textBilingual: { en: "", fr: "" } },
          ];
        }
      } else {
        next[questionIndex].options = [];
      }
      return next;
    });

  const handleOptionChange = (questionIndex, optionIndex, value) =>
    setQuestions((prev) => {
      const next = [...prev];
      if (next[questionIndex].options) {
        next[questionIndex].options[optionIndex] = {
          ...next[questionIndex].options[optionIndex],
          text: value,
          textBilingual: {
            ...next[questionIndex].options[optionIndex].textBilingual,
            [activeLang]: value,
          },
        };
      }
      return next;
    });

  const handleSaveQuestion = (questionIndex) =>
    setQuestions((prev) => {
      const next = [...prev];
      next[questionIndex] = { ...next[questionIndex], saved: true };
      return next;
    });

  const handleEditQuestion = (questionIndex) =>
    setQuestions((prev) => {
      const next = [...prev];
      next[questionIndex] = { ...next[questionIndex], saved: false };
      return next;
    });

  const handleDuplicate = (questionIndex) => {
    const q = questions[questionIndex];
    setQuestions((prev) => [
      ...prev,
      {
        ...q,
        id: `local-${Date.now()}-${Math.random()}`,
        saved: false,
      },
    ]);
  };

  const handleDeleteOption = (questionIndex, optionId) =>
    setQuestions((prev) => {
      const next = [...prev];
      if (next[questionIndex].options) {
        next[questionIndex].options = next[questionIndex].options.filter(
          (opt) => opt.id !== optionId
        );
      }
      return next;
    });

  const onDragEnd = (result) => {
    if (!result.destination) return;
    const items = Array.from(questions);
    const [moved] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, moved);
    setQuestions(items);
  };

  return (
    <CreateSurveyContext.Provider
      value={{
        // identity
        surveyId,
        // fields
        surveyTitle,
        setSurveyTitle,
        surveyDescription,
        setSurveyDescription,
        surveyTitleEn, surveyTitleFr,
        surveyDescEn, surveyDescFr,
        // language
        activeLang,
        setActiveLang,
        // questions
        questions,
        setQuestions,
        defaultQuestionType,
        // quality
        qualityIssueMap,
        surveyLevelIssues,
        // loading
        isSaving,
        isGenerating,
        isAuditing,
        isLoading,
        // actions
        loadSurvey,
        resetSurvey,
        handleSaveSurvey,
        handleGenerate,
        handleAudit,
        // question actions
        addNewQuestion,
        handleDeleteQuestion,
        handleAddOption,
        handleTitleChange,
        handleQuestionTypeChange,
        handleOptionChange,
        handleSaveQuestion,
        handleEditQuestion,
        handleDuplicate,
        handleDeleteOption,
        onDragEnd,
        // sidebar refresh
        setOnSurveyListChanged,
        // legacy compat
        dupList: [],
        handleCreateSurvey: handleSaveSurvey,
      }}
    >
      {children}
    </CreateSurveyContext.Provider>
  );
};

// Legacy mock kept for reference — replaced by CreateSurveyProvider above
export const CreateSurveyProviderMock = CreateSurveyProvider;

export const useCreateSurveyProvider = () => useContext(CreateSurveyContext);
