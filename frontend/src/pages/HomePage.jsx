import { Link } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";

function HomePage() {
  const { edaSummary } = useAnalysis();
  const { isAuthenticated } = useAuth();

  return (
    <main className="page page--home">
      <header className="home-hero">
        <p className="home-hero__eyebrow">Data → decisions</p>

        <h1 className="home-hero__title">LOOM</h1>

        <p className="home-hero__lead">
          <strong>Logical Optimization and Orchestration for Machine Learning.</strong>
          <br />
          LOOM is a guided workspace for tabular CSV data. Upload a file, let the platform
          suggest a target column and model family, then review EDA signals, explainable
          visualizations, and a preprocessing plan you can tune — without leaving the browser.
        </p>

        <div className="home-hero__actions">
          <Link to="/analyze" className="btn btn--primary">
            Start analyzing
          </Link>

          {edaSummary ? (
            <Link to="/results" className="btn btn--ghost">
              View last results
            </Link>
          ) : (
            <span className="btn btn--ghost btn--disabled" aria-disabled="true">
              View last results
            </span>
          )}
        </div>

        <p className="home-hero__account">
          {isAuthenticated ? (
            <>
              Signed in — your workflow is saved under <Link to="/activity">Activity</Link>.
            </>
          ) : (
            <>
              <Link to="/register">Create an account</Link> (email + one-time code) or{" "}
              <Link to="/login">sign in</Link> to record dataset runs, EDA, and charts on the
              Activity page.
            </>
          )}
        </p>
      </header>

      <section className="home-grid" aria-labelledby="how-it-works">
        <h2 id="how-it-works" className="home-grid__heading">
          How LOOM works
        </h2>

        <div className="home-cards">
          <article className="home-card">
            <h3 className="home-card__title">1. Upload &amp; preview</h3>
            <p className="home-card__text">
              Drop a CSV on the Analyze page. You get row and column counts, a compact preview
              you can expand, and a column summary to sanity-check types and missing values.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">2. Target &amp; task</h3>
            <p className="home-card__text">
              LOOM ranks likely targets and infers a task type. If you pick a risky target or
              a task that does not match the column, you will see a warning before you commit.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">3. EDA &amp; preprocessing</h3>
            <p className="home-card__text">
              Run EDA to see risk flags, stability, and quality. The preprocessing plan recommends
              imputation per column from skew, outliers, and missingness — and you can override
              each column’s method while keeping the recommendation visible.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">4. Visualize &amp; explain</h3>
            <p className="home-card__text">
              Open the Visualize page for distribution and correlation charts, or ask Klaus for
              natural-language, explainable visual insights from your uploaded dataset.
            </p>
          </article>
        </div>
      </section>
    </main>
  );
}

export default HomePage;