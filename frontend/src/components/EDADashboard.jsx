function EDADashboard({ edaSummary }) {
  if (!edaSummary) return null;

  const badgeClass = (status) => {
    if (status === "high") return "badge badge--high";
    if (status === "medium") return "badge badge--medium";
    return "badge badge--low";
  };

  const getStabilityLevel = (score) => {
    if (score > 0.6) return "high";
    if (score > 0.3) return "medium";
    return "low";
  };

  const flags = edaSummary.dataset_flags;

  return (
    <section className="section">
      <h2>EDA dashboard</h2>

      <div className="card">
        <h3 className="card__title">Dataset risk summary</h3>
        <div className="badge-row">
          {flags.has_high_missing && (
            <span className={badgeClass("high")}>High missing values</span>
          )}
          {flags.has_high_skew && (
            <span className={badgeClass("medium")}>High skew</span>
          )}
          {flags.has_multicollinearity && (
            <span className={badgeClass("medium")}>Multicollinearity</span>
          )}
          {flags.needs_scaling && (
            <span className={badgeClass("medium")}>Scaling recommended</span>
          )}
          {flags.has_outliers && (
            <span className={badgeClass("medium")}>Outliers detected</span>
          )}
          {!flags.has_high_missing &&
            !flags.has_high_skew &&
            !flags.has_multicollinearity &&
            !flags.needs_scaling &&
            !flags.has_outliers && (
              <span className={badgeClass("low")}>No major risks detected</span>
            )}
        </div>
      </div>

      <div className="card">
        <h3 className="card__title">Dataset overview</h3>
        <p>
          <strong style={{ color: "var(--text)" }}>Rows:</strong> {edaSummary.n_rows}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Features:</strong>{" "}
          {edaSummary.n_features}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Numerical ratio:</strong>{" "}
          {edaSummary.numerical_ratio}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Categorical ratio:</strong>{" "}
          {edaSummary.categorical_ratio}
        </p>
      </div>

      <div className="card">
        <h3 className="card__title">Data quality</h3>
        <p>
          <strong style={{ color: "var(--text)" }}>High missing:</strong>{" "}
          {edaSummary.high_missing_columns.length > 0
            ? edaSummary.high_missing_columns.join(", ")
            : "None"}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Moderate missing:</strong>{" "}
          {edaSummary.moderate_missing_columns.length > 0
            ? edaSummary.moderate_missing_columns.join(", ")
            : "None"}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Low variance:</strong>{" "}
          {edaSummary.low_variance_columns.length > 0
            ? edaSummary.low_variance_columns.join(", ")
            : "None"}
        </p>
      </div>

      <div className="card">
        <h3 className="card__title">Distribution signals</h3>
        <p>
          <strong style={{ color: "var(--text)" }}>High skew columns:</strong>{" "}
          {edaSummary.high_skew_columns.length > 0
            ? edaSummary.high_skew_columns.join(", ")
            : "None"}
        </p>
        <p>
          <strong style={{ color: "var(--text)" }}>Needs scaling:</strong>{" "}
          {edaSummary.dataset_flags.needs_scaling ? "Yes" : "No"}
        </p>
      </div>

      <div className="card">
        <h3 className="card__title">Correlation signals</h3>
        <p>
          <strong style={{ color: "var(--text)" }}>Multicollinearity score:</strong>{" "}
          {edaSummary.multicollinearity_score}
        </p>
        {edaSummary.multicollinearity_pairs.length > 0 && (
          <ul className="insight-list">
            {edaSummary.multicollinearity_pairs.map((pair, index) => (
              <li key={index}>
                {pair.col1} ↔ {pair.col2} (corr: {pair.corr})
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3 className="card__title">Feature stability</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Stability score</th>
                <th>Risk level</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(edaSummary.feature_stability).map(([feature, score]) => {
                const level = getStabilityLevel(score);
                return (
                  <tr key={feature}>
                    <td>{feature}</td>
                    <td>{score}</td>
                    <td>
                      <span className={badgeClass(level)}>
                        {level === "high"
                          ? "High risk"
                          : level === "medium"
                            ? "Moderate"
                            : "Stable"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default EDADashboard;
