import { useCreateSurveyProvider } from "./CreateSurveyProvider";
import React, { useEffect, useState } from "react";
import { PlusIcon2 } from "./Icons";
import QuestionList from "./QuestionList";
import { motion } from "framer-motion";
import AIGenerateModal from "./AIGenerateModal";
import LanguageToggle from "./LanguageToggle";

const CreateSurvey = ({ autoOpenAI = false }) => {
  const {
    questions,
    defaultQuestionType,
    setSurveyTitle,
    setSurveyDescription,
    surveyTitle,
    surveyDescription,
    addNewQuestion,
    handleSaveSurvey,
    handleAudit,
    isSaving,
    isAuditing,
    isLoading,
    surveyId,
    surveyLevelIssues,
    activeLang,
  } = useCreateSurveyProvider();

  const [titleLength, setTitleLength] = useState(0);
  const [descriptionLength, setDescriptionLength] = useState(0);
  const [titleError, setTitleError] = useState("");
  const [descriptionError, setDescriptionError] = useState("");
  const [showAIModal, setShowAIModal] = useState(false);

  // Auto-open modal if navigated with ?ai=true
  useEffect(() => {
    if (autoOpenAI) setShowAIModal(true);
  }, [autoOpenAI]);

  // Sync character counters
  useEffect(() => {
    setTitleLength(surveyTitle?.length || 0);
    setDescriptionLength(surveyDescription?.length || 0);
  }, [surveyTitle, surveyDescription]);


  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3 text-gray-400">
          <svg className="animate-spin w-8 h-8" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm">Loading survey…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full font-switzer lg:overflow-auto scrollbar-style flex-col gap-4 sm:gap-6 sm:p-4">

      {/* ── Action Bar ───────────────────────────────── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <LanguageToggle />
        <div className="flex items-center gap-2">
          {surveyId && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleAudit}
              disabled={isAuditing}
              className="flex items-center gap-1.5 text-xs px-3 py-2 border border-[#6851a7] text-[#6851a7] rounded-full font-medium disabled:opacity-60 transition-all"
            >
              {isAuditing ? (
                <>
                  <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Auditing…
                </>
              ) : (
                "🔍 Audit"
              )}
            </motion.button>
          )}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleSaveSurvey}
            disabled={isSaving}
            className="flex items-center gap-1.5 text-xs px-4 py-2 bg-[#6851a7] text-white rounded-full font-medium shadow-sm disabled:opacity-60 transition-all"
          >
            {isSaving ? (
              <>
                <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Saving…
              </>
            ) : surveyId ? "💾 Save" : "💾 Save Survey"}
          </motion.button>
        </div>
      </div>

      {/* ── Survey-Level Issues Banner ───────────────── */}
      {surveyLevelIssues.length > 0 && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 flex flex-col gap-1">
          <p className="text-xs font-semibold text-amber-700">⚠️ Survey-level issues</p>
          {surveyLevelIssues.map((issue, i) => (
            <p key={i} className="text-xs text-amber-700">
              {activeLang === "fr" ? issue.message_fr : issue.message_en}
            </p>
          ))}
        </div>
      )}

      {/* ── Title & Description ──────────────────────── */}
      <div className="flex flex-col space-y-4">
        <motion.div
          whileHover={{ boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)" }}
          className="rounded-[12px] shadow-sm w-full border border-[#00000020] bg-white flex flex-col transition-all duration-300"
        >
          <motion.input
            type="text"
            maxLength={500}
            name="title"
            value={surveyTitle}
            onChange={(e) => {
              const value = e.target.value;
              setSurveyTitle(value);
              setTitleLength(value.length);
              setTitleError(value.length >= 500 ? "Title cannot exceed 500 characters." : "");
            }}
            placeholder={activeLang === "fr" ? "Titre du sondage" : "Enter survey title"}
            className="text-[16px] px-5 pt-4 pb-1 text-primary outline-none border-none bg-transparent rounded-t-[12px] transition-all duration-200"
          />
          <div className="px-5 pb-3 text-right">
            <p className={`text-[10px] ${titleLength > 450 ? "text-amber-500" : "text-gray-400"}`}>
              {titleLength}/500
            </p>
            {titleError && <p className="text-red-500 text-sm">{titleError}</p>}
          </div>
        </motion.div>

        <motion.div
          whileHover={{ boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)" }}
          className="rounded-[12px] shadow-sm w-full border border-[#00000020] bg-white flex flex-col transition-all duration-300"
        >
          <motion.input
            type="text"
            placeholder={activeLang === "fr" ? "Description du sondage" : "Enter survey description"}
            maxLength={100}
            name="description"
            value={surveyDescription}
            onChange={(e) => {
              const value = e.target.value;
              setSurveyDescription(value);
              setDescriptionLength(value.length);
              setDescriptionError(value.length >= 100 ? "Description cannot exceed 100 characters." : "");
            }}
            className="text-[16px] px-5 pt-4 pb-1 text-primary outline-none border-none bg-transparent rounded-t-[12px] transition-all duration-200"
          />
          <div className="px-5 pb-3 text-right">
            <p className={`text-[10px] ${descriptionLength > 90 ? "text-amber-500" : "text-gray-400"}`}>
              {descriptionLength}/100
            </p>
            {descriptionError && (
              <p className="text-red-500 text-xs">{descriptionError}</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* ── Question List ────────────────────────────── */}
      <div className="flex-1">
        <QuestionList questions={questions} />
      </div>

      {/* ── Bottom Action Buttons ────────────────────── */}
      <div className="flex gap-3">
        {/* Add Question */}
        <motion.div
          whileHover={{ scale: 1.01, borderColor: "#6851a7" }}
          className="flex-1 border-2 py-4 md:py-5 rounded-[12px] flex justify-center border-dotted border-[#6851a7] bg-[#6851a7]/5 transition-all duration-300"
        >
          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0 6px 20px rgba(108, 93, 211, 0.3)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => addNewQuestion(defaultQuestionType)}
            className="bg-[#6851a7] flex gap-2 items-center text-white py-3 px-6 rounded-full shadow-sm transition-all duration-300"
          >
            <PlusIcon2 className="h-4 w-4" />
            <span className="font-medium text-base">Add Question</span>
          </motion.button>
        </motion.div>

        {/* AI Generate */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="border-2 py-4 md:py-5 rounded-[12px] flex justify-center border-dotted border-white bg-gradient-to-br from-[#6851a7]/10 to-[#9b87d1]/10 transition-all duration-300 px-2"
        >
          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0 6px 20px rgba(108, 93, 211, 0.25)" }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowAIModal(true)}
            className="bg-gradient-to-r from-[#6851a7] to-[#9b87d1] flex gap-2 items-center text-white py-3 px-6 rounded-full shadow-sm transition-all duration-300"
          >
            <span>✨</span>
            <span className="font-medium text-base">Generate</span>
          </motion.button>
        </motion.div>
      </div>

      {/* ── AI Generate Modal ────────────────────────── */}
      <AIGenerateModal isOpen={showAIModal} onClose={() => setShowAIModal(false)} />
    </div>
  );
};

export default CreateSurvey;
