import { Navigate, useNavigate } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import Dashboard from "../components/Dashboard";

function VizPage() {
  const { dashboardPayload, setDashboardPayload, datasetDecision, datasetQuality } = useAnalysis();
  const navigate = useNavigate();

  if (!datasetDecision) {
    return <Navigate to="/analyze" replace />;
  }

  if (!dashboardPayload?.panels?.length) {
    return (
      <main className="page page--empty">
        <h1 className="page__title">No dashboard yet</h1>
        <p className="page__subtitle">
          From Analyze, use &quot;Open visualizations&quot; after your CSV is loaded and a target
          is selected.
        </p>
        <button type="button" className="btn btn--primary" onClick={() => navigate("/analyze")}>
          Go to Analyze
        </button>
      </main>
    );
  }

  return (
    <Dashboard
      payload={dashboardPayload}
      qualityScore={datasetQuality?.quality_score}
      onClose={() => {
        setDashboardPayload(null);
        navigate("/analyze");
      }}
    />
  );
}

export default VizPage;
