import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

const SurveyListPage = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center h-full gap-8 p-8 text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center gap-3"
      >
        <div className="w-16 h-16 rounded-2xl bg-[#6851a7]/10 flex items-center justify-center mb-2">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              stroke="#6851a7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9 12h6M9 16h4" stroke="#6851a7" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-primary">Welcome to Boundary AI</h1>
        <p className="text-gray-500 max-w-sm text-sm">
          Select a survey from the sidebar, or create a new one to get started.
        </p>
      </motion.div>

      <div className="flex flex-col sm:flex-row gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate("/surveys/new")}
          className="px-6 py-3 bg-white border-2 border-[#6851a7] text-[#6851a7] rounded-full font-medium text-sm transition-all"
        >
          + Create Manually
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate("/surveys/new?ai=true")}
          className="px-6 py-3 bg-[#6851a7] text-white rounded-full font-medium text-sm shadow-md transition-all"
        >
          ✨ Generate with AI
        </motion.button>
      </div>
    </div>
  );
};

export default SurveyListPage;
