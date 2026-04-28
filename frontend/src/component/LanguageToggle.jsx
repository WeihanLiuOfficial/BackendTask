import React from "react";
import { motion } from "framer-motion";
import { useCreateSurveyProvider } from "./CreateSurveyProvider";

/**
 * EN / FR toggle button.
 * Reads and sets activeLang from the survey context.
 */
const LanguageToggle = () => {
  const { activeLang, setActiveLang } = useCreateSurveyProvider();

  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-full p-0.5">
      {["en", "fr"].map((lang) => (
        <motion.button
          key={lang}
          onClick={() => setActiveLang(lang)}
          whileTap={{ scale: 0.95 }}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200 ${
            activeLang === lang
              ? "bg-[#6851a7] text-white shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {lang.toUpperCase()}
        </motion.button>
      ))}
    </div>
  );
};

export default LanguageToggle;
