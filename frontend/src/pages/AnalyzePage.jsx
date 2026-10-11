import UploadSection from "../components/UploadSection";
import DecisionPanel from "../components/DecisionPanel";

function AnalyzePage() {
  return (
    <main className="page page--analyze">
      <header className="page__intro">
        <h1 className="page__title">Analyze</h1>
        <p className="page__subtitle">
          Upload your CSV on the left. Configure target and task in the center — warnings appear
          if your choices look misaligned with the data.
        </p>
      </header>

      <div className="analyze-workspace">
        <aside className="analyze-sidebar" aria-label="Dataset upload and preview">
          <UploadSection compact />
        </aside>
        <div className="analyze-main">
          <DecisionPanel variant="centered" />
        </div>
      </div>
    </main>
  );
}

export default AnalyzePage;
