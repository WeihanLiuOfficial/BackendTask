import React from "react";
import { motion, AnimatePresence } from "framer-motion";

const severityConfig = {
  critical: {
    bg: "bg-red-50",
    border: "border-red-400",
    badge: "bg-red-100 text-red-700",
    icon: "⛔",
    label: "Critical",
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-400",
    badge: "bg-amber-100 text-amber-700",
    icon: "⚠️",
    label: "Warning",
  },
  info: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    badge: "bg-blue-100 text-blue-700",
    icon: "ℹ️",
    label: "Info",
  },
};

/**
 * Renders quality issue warnings directly below a question card.
 *
 * @param {{ issues: Array<{severity, message_en, message_fr}>, lang: 'en'|'fr' }} props
 */
const QualityIssueBox = ({ issues, lang = "en" }) => {
  if (!issues || issues.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -6, height: 0 }}
        animate={{ opacity: 1, y: 0, height: "auto" }}
        exit={{ opacity: 0, y: -4, height: 0 }}
        transition={{ duration: 0.25 }}
        className="flex flex-col gap-2 mt-1 mb-3"
      >
        {issues.map((issue, i) => {
          const cfg = severityConfig[issue.severity] || severityConfig.info;
          const message = lang === "fr" ? issue.message_fr : issue.message_en;
          return (
            <div
              key={i}
              className={`flex items-start gap-2 px-3 py-2 rounded-lg border ${cfg.bg} ${cfg.border}`}
            >
              <span className="text-sm leading-5 mt-0.5">{cfg.icon}</span>
              <div className="flex-1 min-w-0">
                <span
                  className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full mr-2 ${cfg.badge}`}
                >
                  {cfg.label}
                </span>
                <span className="text-xs text-gray-700 leading-5">{message}</span>
              </div>
            </div>
          );
        })}
      </motion.div>
    </AnimatePresence>
  );
};

export default QualityIssueBox;
