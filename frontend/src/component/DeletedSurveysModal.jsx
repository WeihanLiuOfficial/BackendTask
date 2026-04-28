import React, { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { getDeletedSurveys, restoreSurvey, permanentlyDeleteSurvey } from "../api/apiClient";

/**
 * Recently Deleted panel — shows soft-deleted surveys with Restore and
 * Permanently Delete actions.
 *
 * Props:
 *   isOpen        {boolean}   — whether the panel is visible
 *   onClose       {function}  — called when the user dismisses the panel
 *   onRestored    {function}  — called after a successful restore so the
 *                               sidebar survey list can refresh
 */
const DeletedSurveysModal = ({ isOpen, onClose, onRestored }) => {
  const [deletedSurveys, setDeletedSurveys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [confirmId, setConfirmId] = useState(null); // id awaiting permanent-delete confirm

  const fetchDeleted = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDeletedSurveys();
      setDeletedSurveys(data.surveys || []);
    } catch (err) {
      toast.error("Failed to load recently deleted surveys.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchDeleted();
    } else {
      // Reset pending-confirm state so reopening the panel never shows
      // a stale confirmation dialog from a previous interaction.
      setConfirmId(null);
    }
  }, [isOpen, fetchDeleted]);

  const handleRestore = async (id) => {
    try {
      await restoreSurvey(id);
      toast.success("Survey restored.");
      setDeletedSurveys((prev) => prev.filter((s) => s.id !== id));
      onRestored?.();
    } catch (err) {
      toast.error("Failed to restore survey.");
    }
  };

  const handlePermanentDelete = async (id) => {
    try {
      await permanentlyDeleteSurvey(id);
      toast.success("Survey permanently deleted.");
      setDeletedSurveys((prev) => prev.filter((s) => s.id !== id));
      setConfirmId(null);
    } catch (err) {
      toast.error("Failed to permanently delete survey.");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="panel"
          initial={{ opacity: 0, y: 12, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.97 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="fixed bottom-14 left-2 z-50 w-64 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <span className="text-base">🗑️</span>
                <h3 className="text-sm font-semibold text-gray-800">Recently Deleted</h3>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors text-lg leading-none"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="max-h-72 overflow-y-auto">
              {loading ? (
                <div className="flex flex-col gap-2 p-3">
                  {[1, 2].map((i) => (
                    <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
                  ))}
                </div>
              ) : deletedSurveys.length === 0 ? (
                <p className="text-gray-400 text-xs text-center py-8 px-4">
                  No recently deleted surveys.
                </p>
              ) : (
                <div className="flex flex-col divide-y divide-gray-50">
                  <AnimatePresence>
                    {deletedSurveys.map((survey) => {
                      const title =
                        survey.title?.en || survey.title?.fr || "Untitled Survey";
                      const isPendingConfirm = confirmId === survey.id;

                      return (
                        <motion.div
                          key={survey.id}
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.15 }}
                          className="px-3 py-2.5"
                        >
                          <p
                            className="text-xs font-medium text-gray-700 truncate mb-1.5"
                            title={title}
                          >
                            {title}
                          </p>

                          {isPendingConfirm ? (
                            /* Permanent delete confirmation */
                            <div className="flex flex-col gap-1">
                              <p className="text-[10px] text-red-500 font-medium">
                                This cannot be undone. Confirm?
                              </p>
                              <div className="flex gap-1.5">
                                <button
                                  onClick={() => handlePermanentDelete(survey.id)}
                                  className="flex-1 text-[10px] py-1 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors font-semibold"
                                >
                                  Yes, delete forever
                                </button>
                                <button
                                  onClick={() => setConfirmId(null)}
                                  className="flex-1 text-[10px] py-1 bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200 transition-colors"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            /* Normal action row */
                            <div className="flex gap-1.5">
                              <button
                                onClick={() => handleRestore(survey.id)}
                                className="flex-1 text-[10px] py-1 bg-[#6851a7] text-white rounded-md hover:bg-[#5a4490] transition-colors font-medium"
                              >
                                Restore
                              </button>
                              <button
                                onClick={() => setConfirmId(survey.id)}
                                className="flex-1 text-[10px] py-1 bg-red-50 text-red-500 rounded-md hover:bg-red-100 transition-colors font-medium border border-red-200"
                              >
                                Delete forever
                              </button>
                            </div>
                          )}
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </motion.div>
      )}
    </AnimatePresence>
  );
};

export default DeletedSurveysModal;
