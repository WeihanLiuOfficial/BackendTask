import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { getSurveys, softDeleteSurvey } from "../api/apiClient";
import { useCreateSurveyProvider } from "./CreateSurveyProvider";
import DeletedSurveysModal from "./DeletedSurveysModal";

const Sidebar = ({ isSidebarShow, setSidebarShow }) => {
  const navigate = useNavigate();
  const { id: currentId } = useParams();
  const { setOnSurveyListChanged, resetSurvey } = useCreateSurveyProvider();

  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hoveredId, setHoveredId] = useState(null);
  const [showDeletedModal, setShowDeletedModal] = useState(false);

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

  const handleSoftDelete = async (e, survey) => {
    // Prevent the click from bubbling up to the survey button (which would navigate)
    e.stopPropagation();
    try {
      await softDeleteSurvey(survey.id);
      toast.success(`"${survey.title?.en || survey.title?.fr || "Survey"}" moved to Recently Deleted.`);
      // If the deleted survey is currently open, navigate away
      if (survey.id === currentId) {
        resetSurvey();
        navigate("/surveys/new");
      }
      fetchSurveys();
    } catch (err) {
      toast.error("Failed to delete survey.");
    }
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
        <div className="flex-1 overflow-y-auto px-2 pb-2">
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
                  const isHovered = hoveredId === survey.id;
                  const title = survey.title?.en || survey.title?.fr || "Untitled Survey";
                  const hasIssues = survey.has_quality_issues;

                  return (
                    <motion.div
                      key={survey.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      className="flex items-center rounded-lg overflow-hidden"
                      onMouseEnter={() => setHoveredId(survey.id)}
                      onMouseLeave={() => setHoveredId(null)}
                    >
                      {/* Survey navigation button */}
                      <button
                        onClick={() => handleSelectSurvey(survey.id)}
                        className={`flex-1 text-left pl-3 pr-2 py-2.5 text-xs flex items-center gap-2 transition-all duration-150 min-w-0 ${
                          isActive
                            ? "bg-white/20 text-white font-medium"
                            : "text-white/70 hover:bg-white/10 hover:text-white"
                        } ${hasIssues ? "border-l-2 border-red-400" : ""}`}
                      >
                        {hasIssues && (
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                        )}
                        <span className="truncate flex-1">{title}</span>
                      </button>

                      {/* Soft delete button — visible on hover, inline with the row */}
                      <AnimatePresence>
                        {isHovered && (
                          <motion.button
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "1.75rem" }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={{ duration: 0.12 }}
                            onClick={(e) => handleSoftDelete(e, survey)}
                            title="Move to Recently Deleted"
                            className={`flex-shrink-0 h-full py-2.5 flex items-center justify-center text-white/50 hover:text-white hover:bg-red-500/70 transition-colors overflow-hidden ${
                              isActive ? "bg-white/20" : "hover:bg-red-500/70"
                            }`}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                              className="w-3.5 h-3.5 flex-shrink-0"
                            >
                              <path
                                fillRule="evenodd"
                                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                                clipRule="evenodd"
                              />
                            </svg>
                          </motion.button>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Footer — Recently Deleted button */}
        <div className="px-3 py-3 border-t border-white/10">
          <button
            onClick={() => setShowDeletedModal((prev) => !prev)}
            className="w-full text-xs py-2 px-3 text-white/50 hover:text-white/80 rounded-lg flex items-center gap-2 hover:bg-white/5 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-3.5 h-3.5 flex-shrink-0"
            >
              <path
                fillRule="evenodd"
                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                clipRule="evenodd"
              />
            </svg>
            Recently Deleted
          </button>
        </div>
      </aside>

      {/* Recently Deleted panel */}
      <DeletedSurveysModal
        isOpen={showDeletedModal}
        onClose={() => setShowDeletedModal(false)}
        onRestored={fetchSurveys}
      />

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
