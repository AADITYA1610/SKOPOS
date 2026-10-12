import { Link } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";

function HomePage() {
  const { edaSummary } = useAnalysis();
  const { isAuthenticated } = useAuth();

  return (
    <main className="page page--home">
      <header className="home-hero">
        <p className="home-hero__eyebrow">
          Research data preparation and quality monitoring
        </p>

        <h1 className="home-hero__title">SKOPOS</h1>

        <p className="home-hero__lead">
          <strong>
            An Explainable AI-Driven Adaptive Platform for Research Data
          </strong>
          <br />
          Explore and prepare uploaded CSV datasets, review preprocessing
          recommendations, and monitor simulated sensor readings as they
          arrive. Inspect quality issues and original measurements through
          an interactive workspace.
        </p>

        <div className="home-hero__actions">
          <Link to="/analyze" className="btn btn--primary">
            Analyze a CSV
          </Link>

          <Link to="/streams" className="btn btn--ghost">
            Try live stream demo
          </Link>

          {edaSummary && (
            <Link to="/results" className="btn btn--ghost">
              View last results
            </Link>
          )}
        </div>

        <p className="home-hero__account">
          {isAuthenticated ? (
            <>
              View your recorded dataset actions on the{" "}
              <Link to="/activity">Activity</Link> page.
            </>
          ) : (
            <>
              <Link to="/register">Create an account</Link> or{" "}
              <Link to="/login">sign in</Link> to record dataset runs,
              EDA, and chart activity.
            </>
          )}
        </p>
      </header>

      <section className="home-grid" aria-labelledby="current-workflows">
        <h2 id="current-workflows" className="home-grid__heading">
          Explore the current prototype
        </h2>

        <div className="home-cards">
          <article className="home-card">
            <h3 className="home-card__title">
              CSV analysis
            </h3>
            <p className="home-card__text">
              Upload a CSV to preview its contents and inspect column
              types and missing values. Review suggested target variables,
              task types, and model families.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">
              Guided preprocessing
            </h3>
            <p className="home-card__text">
              Use EDA signals to review preprocessing recommendations.
              Adjust imputation methods, execute the supported
              transformations, and download the processed CSV.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">
              Visualization and KLAUS
            </h3>
            <p className="home-card__text">
              Explore distribution and correlation charts or build custom
              visualizations. Ask KLAUS to turn a natural-language request
              into a chart for your uploaded dataset.
            </p>
          </article>

          <article className="home-card">
            <h3 className="home-card__title">
              Simulated stream monitoring
            </h3>
            <p className="home-card__text">
              Start a demo with one click. Watch successive readings,
              live charts, and quality summaries for the latest 10
              arrivals. Missing measurements, range violations, and
              repeated event identities are flagged.
            </p>
          </article>
        </div>
      </section>

      <section
        className="home-grid"
        aria-labelledby="development-roadmap"
        style={{ marginTop: "32px" }}
      >
        <h2 id="development-roadmap" className="home-grid__heading">
          Next stages of development
        </h2>

        <p className="home-card__text">
          Planned extensions include external API and physical sensor
          connections, persistent stream storage, researcher-approved
          stream cleaning, statistical anomaly and drift monitoring,
          richer KLAUS assistance, and image and video data workflows.
          These extensions are not available in the current prototype.
        </p>
      </section>
    </main>
  );
}

export default HomePage;