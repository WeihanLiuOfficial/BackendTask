import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { CreateSurveyProvider } from "./component/CreateSurveyProvider";
import CreateSurveyPage from "./pages/CreateSurveyPage";
import SurveyListPage from "./pages/SurveyListPage";
import DashboardLayout from "./component/DashboardLayout";

function App() {
  return (
    <BrowserRouter>
      <CreateSurveyProvider>
        {/* Global toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              fontSize: "13px",
              borderRadius: "10px",
              boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
            },
            success: { iconTheme: { primary: "#6851a7", secondary: "#fff" } },
          }}
        />

        <Routes>
          {/* Default → surveys list */}
          <Route path="/" element={<Navigate to="/surveys" replace />} />

          {/* Landing: no survey selected */}
          <Route
            path="/surveys"
            element={
              <DashboardLayout>
                <SurveyListPage />
              </DashboardLayout>
            }
          />

          {/* New survey (manual or AI via ?ai=true) */}
          <Route path="/surveys/new" element={<CreateSurveyPage />} />

          {/* Edit existing survey */}
          <Route path="/surveys/:id" element={<CreateSurveyPage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/surveys" replace />} />
        </Routes>
      </CreateSurveyProvider>
    </BrowserRouter>
  );
}

export default App;
