import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCreateSurveyProvider } from "./CreateSurveyProvider";

/**
 * AI Generation Modal.
 *
 * Triggered by the "✨ Generate" button in CreateSurvey.
 * Calls generation_service via the context's handleGenerate().
 */
const AIGenerateModal = ({ isOpen, onClose }) => {
  const { handleGenerate, isGenerating, questions } = useCreateSurveyProvider();

  const [prompt, setPrompt] = useState("");
  const [questionCount, setQuestionCount] = useState("");
  const [addMore, setAddMore] = useState(false);

  const hasExistingQuestions = questions.length > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    await handleGenerate(prompt.trim(), questionCount ? parseInt(questionCount) : null, addMore);
    // Modal closes itself via onClose called inside handleGenerate on success
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={!isGenerating ? onClose : undefined}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 flex flex-col gap-5">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-primary">✨ Generate with AI</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Describe your survey topic — the AI will create bilingual questions for you.
                  </p>
                </div>
                {!isGenerating && (
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 text-xl leading-none p-1"
                  >
                    ✕
                  </button>
                )}
              </div>

              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                {/* Prompt */}
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700">
                    Survey description <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    disabled={isGenerating}
                    placeholder="e.g. Customer satisfaction survey for an online clothing store"
                    rows={3}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-[#6851a7]/30 focus:border-[#6851a7] resize-none transition-all disabled:opacity-60"
                    required
                  />
                </div>

                {/* Question Count */}
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700">
                    Number of questions{" "}
                    <span className="text-gray-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={questionCount}
                    onChange={(e) => setQuestionCount(e.target.value)}
                    disabled={isGenerating}
                    placeholder="AI decides (typically 5–12)"
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-[#6851a7]/30 focus:border-[#6851a7] transition-all disabled:opacity-60"
                  />
                </div>

                {/* Add more toggle — only if questions exist */}
                {hasExistingQuestions && (
                  <label className="flex items-center gap-3 cursor-pointer">
                    <div
                      onClick={() => !isGenerating && setAddMore((v) => !v)}
                      className={`w-10 h-5 rounded-full transition-colors duration-200 flex items-center px-0.5 ${
                        addMore ? "bg-[#6851a7]" : "bg-gray-200"
                      }`}
                    >
                      <motion.div
                        animate={{ x: addMore ? 18 : 0 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        className="w-4 h-4 bg-white rounded-full shadow"
                      />
                    </div>
                    <span className="text-sm text-gray-700">
                      Keep existing questions and add more
                    </span>
                  </label>
                )}

                {/* Submit */}
                <motion.button
                  type="submit"
                  disabled={isGenerating || !prompt.trim()}
                  whileHover={!isGenerating ? { scale: 1.01 } : {}}
                  whileTap={!isGenerating ? { scale: 0.98 } : {}}
                  className="w-full py-3 bg-[#6851a7] hover:bg-[#5b4691] text-white rounded-xl font-medium text-sm shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isGenerating ? (
                    <>
                      <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                      Generating…
                    </>
                  ) : (
                    "✨ Generate Survey"
                  )}
                </motion.button>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default AIGenerateModal;
