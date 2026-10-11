import { Link } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import EDADashboard from "../components/EDADashboard";
import PreprocessingPlan from "../components/PreprocessingPlan";

function ResultsPage() {
  const { edaSummary, preprocessingPlan, datasetQuality, insights } = useAnalysis();

  if (!edaSummary) {
    return (
      <main className="page page--empty">
        <h1 className="page__title">No results yet</h1>
        <p className="page__subtitle">
          Run EDA from the Analyze page after choosing a target. Your summaries and preprocessing
          plan will show up here.
        </p>
        <Link to="/analyze" className="btn btn--primary">
          Go to Analyze
        </Link>
      </main>
    );
  }

  return (
    <main className="page page--results">
      <header className="page__intro">
        <h1 className="page__title">Results</h1>
        <p className="page__subtitle">
          Exploratory signals, quality, insights, and a tunable preprocessing plan.
        </p>
      </header>

      <div className="app__grid">
        <div>
          <EDADashboard edaSummary={edaSummary} />
          {preprocessingPlan && <PreprocessingPlan plan={preprocessingPlan} />}
        </div>

        <div>
          {datasetQuality && (
            <div className="card section">
              <h3 className="card__title">Dataset quality score</h3>
              <p className="metric-value">
                {datasetQuality.quality_score}
                <span className="metric-suffix"> / 100</span>
              </p>
            </div>
          )}

          {insights && (
            <div className="card section">
              <h3 className="card__title">Dataset insights</h3>
              <ul className="insight-list">
                {insights.map((insight, i) => (
                  <li key={i}>{insight}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="card section">
            <h3 className="card__title">Next step</h3>
            <p>Open charts for your current target on the Visualize page.</p>
            <Link to="/visualize" className="btn btn--primary" style={{ marginTop: "0.75rem" }}>
              Open visualizations
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

export default ResultsPage;
