import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { getSurveys } from "../api/apiClient";
import { useCreateSurveyProvider } from "./CreateSurveyProvider";

const Sidebar = ({ isSidebarShow, setSidebarShow }) => {
  const navigate = useNavigate();
  const { id: currentId } = useParams();
  const { setOnSurveyListChanged, resetSurvey } = useCreateSurveyProvider();

  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSurveys = useCallback(async () => {
    try {
      const data = await getSurveys();
      setSurveys(data.surveys || []);
    } catch (err) {
      console.error("Failed to load surveys:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSurveys();
    // Register refresh callback so Provider can trigger sidebar reload after Save/Generate
    setOnSurveyListChanged(fetchSurveys);
    return () => setOnSurveyListChanged(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchSurveys]); // setOnSurveyListChanged intentionally omitted — it's stable (useCallback)

  const handleNewSurvey = () => {
    resetSurvey();
    navigate("/surveys/new");
    setSidebarShow(false);
  };

  const handleAIGenerate = () => {
    resetSurvey();
    navigate("/surveys/new?ai=true");
    setSidebarShow(false);
  };

  const handleSelectSurvey = (id) => {
    navigate(`/surveys/${id}`);
    setSidebarShow(false);
  };

  return (
    <>
      <aside
        className={`${
          isSidebarShow ? "translate-x-0" : "-translate-x-full xl:translate-x-0"
        } fixed left-0 top-0 xl:static max-w-[220px] min-w-[220px] h-screen overflow-hidden bg-primary transition-all duration-300 ease-in-out z-50 flex flex-col`}
      >
        {/* Logo / Header */}
        <div className="px-4 lg:px-5 pt-5 pb-3 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-white text-sm font-semibold tracking-wide">Boundary AI</h2>
            <button
              className="xl:hidden text-white/70 hover:text-white"
              onClick={() => setSidebarShow(false)}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-3 pt-4 pb-3 flex flex-col gap-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleAIGenerate}
            className="w-full text-xs py-2 px-3 bg-white text-[#6851a7] rounded-lg font-semibold flex items-center gap-1.5 shadow-sm"
          >
            <span>✨</span> Generate with AI
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleNewSurvey}
            className="w-full text-xs py-2 px-3 bg-white/10 text-white rounded-lg font-medium flex items-center gap-1.5 hover:bg-white/20 transition-colors"
          >
            <span>+</span> New Survey
          </motion.button>
        </div>

        {/* Survey List */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          <p className="text-white/50 text-[10px] uppercase tracking-wider px-2 mb-2">
            Saved Surveys
          </p>

          {loading ? (
            <div className="flex flex-col gap-2 px-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-10 bg-white/10 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : surveys.length === 0 ? (
            <p className="text-white/40 text-xs px-2 italic">No surveys yet.</p>
          ) : (
            <div className="flex flex-col gap-1">
              <AnimatePresence>
                {surveys.map((survey) => {
                  const isActive = survey.id === currentId;
                  const title = survey.title?.en || survey.title?.fr || "Untitled Survey";
                  const hasIssues = survey.has_quality_issues;

                  return (
                    <motion.button
                      key={survey.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      onClick={() => handleSelectSurvey(survey.id)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-xs flex items-center gap-2 transition-all duration-150 ${
                        isActive
                          ? "bg-white/20 text-white font-medium"
                          : "text-white/70 hover:bg-white/10 hover:text-white"
                      } ${hasIssues ? "border-l-2 border-red-400" : ""}`}
                    >
                      {/* Red dot for quality issues */}
                      {hasIssues && (
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                      )}
                      <span className="truncate flex-1">{title}</span>
                    </motion.button>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile backdrop */}
      {isSidebarShow && (
        <div
          onClick={() => setSidebarShow(false)}
          className="fixed inset-0 bg-primary/30 z-10 xl:hidden"
        />
      )}
    </>
  );
};

export default Sidebar;
