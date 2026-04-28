import React, { useEffect, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import DashboardLayout from "../component/DashboardLayout";
import CreateSurvey from "../component/CreateSurvey";
import CreateSurveySidebar from "../component/CreateSurveySidebar";
import Header from "../component/Header";
import { useCreateSurveyProvider } from "../component/CreateSurveyProvider";

const CreateSurveyPageInner = () => {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const aiMode = searchParams.get("ai") === "true";
  const { loadSurvey, resetSurvey } = useCreateSurveyProvider();
  const prevId = useRef(null);

  useEffect(() => {
    if (id && id !== prevId.current) {
      prevId.current = id;
      loadSurvey(id);
    } else if (!id) {
      prevId.current = null;
      resetSurvey();
    }
  }, [id, loadSurvey, resetSurvey]);

  return (
    <div className="flex flex-col w-full h-full overflow-hidden">
      <div className="lg:min-h-[90px]">
        <Header>
          <h2 className="text-[26px] font-switzerMedium text-primary">
            {id ? "Edit Survey" : "Create a New Survey"}
          </h2>
        </Header>
      </div>
      <div className="flex grow w-full overflow-hidden h-full">
        <div className="grow p-3 sm:p-2 w-full overflow-auto h-[calc(100vh-164px)] sm:h-[calc(100vh-192px)] md:h-[calc(100vh-192px)] lg:h-[calc(100vh-148px)] xl:h-full scrollbar-style">
          <div className="block lg:hidden">
            <CreateSurveySidebar />
          </div>
          <CreateSurvey autoOpenAI={aiMode} />
        </div>
        <div className="hidden lg:block min-w-[280px] p-3 max-w-[280px] overflow-auto scrollbar-style h-[calc(100vh-89px)]">
          <CreateSurveySidebar />
        </div>
      </div>
    </div>
  );
};

const CreateSurveyPage = () => (
  <DashboardLayout>
    <CreateSurveyPageInner />
  </DashboardLayout>
);

export default CreateSurveyPage;
