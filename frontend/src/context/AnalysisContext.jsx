import { createContext, useContext, useCallback, useMemo, useState } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [file, setFile] = useState(null);
  const [datasetDecision, setDatasetDecision] = useState(null);
  const [edaSummary, setEdaSummary] = useState(null);
  const [preprocessingPlan, setPreprocessingPlan] = useState(null);

  const [dashboardPayload, setDashboardPayload] = useState(null);
  const [insights, setInsights] = useState(null);
  const [datasetQuality, setDatasetQuality] = useState(null);

  const [pipelineParams, setPipelineParams] = useState(null);

  // NEW: stores /execute-pipeline result
  const [pipelineResult, setPipelineResult] = useState(null);

  const resetAfterNewUpload = useCallback(() => {
    setEdaSummary(null);
    setPreprocessingPlan(null);
    setDashboardPayload(null);
    setInsights(null);
    setDatasetQuality(null);
    setPipelineParams(null);
    setPipelineResult(null);
  }, []);

  const value = useMemo(
    () => ({
      file,
      setFile,

      datasetDecision,
      setDatasetDecision,

      edaSummary,
      setEdaSummary,

      preprocessingPlan,
      setPreprocessingPlan,

      dashboardPayload,
      setDashboardPayload,

      insights,
      setInsights,

      datasetQuality,
      setDatasetQuality,

      pipelineParams,
      setPipelineParams,

      pipelineResult,
      setPipelineResult,

      resetAfterNewUpload,
    }),
    [
      file,
      datasetDecision,
      edaSummary,
      preprocessingPlan,
      dashboardPayload,
      insights,
      datasetQuality,
      pipelineParams,
      pipelineResult,
      resetAfterNewUpload,
    ]
  );

  return (
    <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext);
  if (!ctx) {
    throw new Error("useAnalysis must be used within AnalysisProvider");
  }
  return ctx;
}