import { useCallback, useEffect, useState } from "react";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";

const METHOD_LABELS = {
  median: "Median",
  mean: "Mean",
  knn: "k-NN imputation",
  constant: "Constant fill",
  most_frequent: "Mode (most frequent)",
};

function labelMethod(m) {
  return METHOD_LABELS[m] || m;
}

function collectImputationOverrides(plan) {
  const overrides = {};

  Object.entries(plan?.imputation || {}).forEach(([col, info]) => {
    if (
      info.method &&
      info.recommended_method &&
      info.method !== info.recommended_method
    ) {
      overrides[col] = info.method;
    }
  });

  return overrides;
}

function downloadCsv(csv, filename = "loom_processed_dataset.csv") {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

function formatScore(score) {
  if (score === null || score === undefined) return "N/A";
  return Number(score).toFixed(4);
}

function formatImprovement(result) {
  if (!result) return "N/A";

  const improvement =
    result.improvement !== null && result.improvement !== undefined
      ? result.improvement
      : "N/A";

  const percentage =
    result.improvement_percentage !== null &&
    result.improvement_percentage !== undefined
      ? ` (${result.improvement_percentage}%)`
      : "";

  return `${improvement}${percentage}`;
}

function getImprovementLabel(result) {
  if (!result || result.improvement === null || result.improvement === undefined) {
    return "Improvement";
  }

  if (result.improvement > 0) return "Improvement";
  if (result.improvement < 0) return "Performance change";
  return "No change";
}

function getImprovementNote(result) {
  if (!result || result.improvement === null || result.improvement === undefined) {
    return null;
  }

  if (result.improvement > 0) {
    return "The preprocessing strategy improved the model score.";
  }

  if (result.improvement < 0) {
    return "The processed dataset scored lower than the baseline. This can happen when preprocessing removes or distorts useful signal for the selected model.";
  }

  return "The preprocessing strategy produced the same score as the baseline.";
}

function PreprocessingPlan({ plan }) {
  const {
    file,
    pipelineParams,
    setPreprocessingPlan,
    pipelineResult,
    setPipelineResult,
  } = useAnalysis();

  const { logActivity } = useAuth();

  const [busyCol, setBusyCol] = useState(null);
  const [planError, setPlanError] = useState(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState(null);

  const refreshPlan = useCallback(
    async (imputationOverrides) => {
      if (!file || !pipelineParams?.target) return;

      const formData = new FormData();
      formData.append("file", file);
      formData.append("target_col", pipelineParams.target);
      formData.append("task_type", pipelineParams.task || "");
      formData.append("model_family", pipelineParams.model || "");
      formData.append(
        "imputation_overrides",
        JSON.stringify(imputationOverrides || {})
      );

      const res = await api.post("/generate-preprocessing-plan", formData);
      setPreprocessingPlan(res.data);
      setPipelineResult(null);
    },
    [file, pipelineParams, setPreprocessingPlan, setPipelineResult]
  );

  useEffect(() => {
    setPlanError(null);
    setPipelineError(null);
  }, [plan]);

  if (!plan) return null;

  const imputationEntries = Object.entries(plan.imputation || {});

  const handleImputationChange = async (col, method) => {
    const next = {};

    Object.entries(plan.imputation || {}).forEach(([c, info]) => {
      const effective = c === col ? method : info.method;

      if (effective !== info.recommended_method) {
        next[c] = effective;
      }
    });

    setBusyCol(col);
    setPlanError(null);

    try {
      await refreshPlan(next);
      void logActivity("imputation_customized", { column: col, method });
    } catch (e) {
      console.error(e);
      setPlanError("Could not update the plan. Check the API.");
    } finally {
      setBusyCol(null);
    }
  };

  const resetAllImputation = async () => {
    setBusyCol("__all__");
    setPlanError(null);

    try {
      await refreshPlan({});
      void logActivity("imputation_customized", { reset_all: true });
    } catch (e) {
      console.error(e);
      setPlanError("Could not reset imputation.");
    } finally {
      setBusyCol(null);
    }
  };

  const runFullPipeline = async () => {
    if (!file || !pipelineParams?.target) {
      setPipelineError("Missing file or target column. Please run EDA again.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_col", pipelineParams.target);
    formData.append("task_type", pipelineParams.task || "");
    formData.append("model_family", pipelineParams.model || "");
    formData.append(
      "imputation_overrides",
      JSON.stringify(collectImputationOverrides(plan))
    );

    setPipelineLoading(true);
    setPipelineError(null);

    try {
      const res = await api.post("/execute-pipeline", formData);

      if (res.data?.error) {
        setPipelineError(res.data.error);
        return;
      }

      setPipelineResult(res.data);

      void logActivity("pipeline_executed", {
        target: pipelineParams.target,
        task: pipelineParams.task,
        model_family: pipelineParams.model,
        before_score: res.data.before_score,
        after_score: res.data.after_score,
      });
    } catch (e) {
      console.error(e);
      setPipelineError(
        e.response?.data?.detail ||
          "Could not execute pipeline. Check backend logs."
      );
    } finally {
      setPipelineLoading(false);
    }
  };

  const previewRows = pipelineResult?.preview || [];
  const previewColumns =
    pipelineResult?.columns?.slice(0, 8) ||
    (previewRows[0] ? Object.keys(previewRows[0]).slice(0, 8) : []);

  const improvementNote = getImprovementNote(pipelineResult);

  return (
    <section className="section">
      <h2>Preprocessing strategy</h2>

      <p style={{ marginTop: "-0.25rem", marginBottom: "1rem" }}>
        Auto-generated steps based on missing values, skewness, outliers,
        categorical risk, scaling need, and model requirements.
      </p>

      <div className="card card--accent">
        <h3 className="card__title">Execute full pipeline</h3>

        <p>
          Apply the preprocessing plan to the uploaded dataset, evaluate baseline
          vs processed performance, preview the transformed data, and download
          the final CSV.
        </p>

        {pipelineError && (
          <div
            className="alert alert--error"
            role="alert"
            style={{ marginTop: "1rem" }}
          >
            {pipelineError}
          </div>
        )}

        <div className="btn-group" style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="btn btn--primary"
            disabled={pipelineLoading}
            onClick={runFullPipeline}
          >
            {pipelineLoading ? "Executing pipeline…" : "Run full pipeline"}
          </button>

          {pipelineResult?.csv && (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => downloadCsv(pipelineResult.csv)}
            >
              Download processed CSV
            </button>
          )}
        </div>
      </div>

      {pipelineResult && (
        <div className="card pipeline-results-card">
          <div className="pipeline-results-head">
            <div>
              <h3 className="card__title">Pipeline results</h3>
              <p className="text-muted">
                Baseline model performance compared against the processed
                dataset.
              </p>
            </div>

            {pipelineResult.metric && (
              <span className="pipeline-metric-pill">
                Metric: {pipelineResult.metric}
              </span>
            )}
          </div>

          <div className="metric-grid">
            <div className="metric-card">
              <span className="metric-card__label">Before preprocessing</span>
              <span className="metric-card__value">
                {formatScore(pipelineResult.before_score)}
              </span>
            </div>

            <div className="metric-card">
              <span className="metric-card__label">After preprocessing</span>
              <span className="metric-card__value">
                {formatScore(pipelineResult.after_score)}
              </span>
            </div>

            <div
              className={
                pipelineResult.improvement < 0
                  ? "metric-card metric-card--warning"
                  : "metric-card metric-card--success"
              }
            >
              <span className="metric-card__label">
                {getImprovementLabel(pipelineResult)}
              </span>
              <span className="metric-card__value">
                {formatImprovement(pipelineResult)}
              </span>
            </div>

            <div className="metric-card">
              <span className="metric-card__label">Processed shape</span>
              <span className="metric-card__value">
                {pipelineResult.shape?.rows ?? "N/A"} ×{" "}
                {pipelineResult.shape?.columns ?? "N/A"}
              </span>
            </div>
          </div>

          {improvementNote && (
            <p className="text-muted" style={{ marginTop: "1rem" }}>
              {improvementNote}
            </p>
          )}

          {(pipelineResult.before_evaluation?.evaluation_method ||
            pipelineResult.after_evaluation?.evaluation_method) && (
            <p className="text-muted" style={{ marginTop: "0.5rem" }}>
              Evaluation:{" "}
              {pipelineResult.after_evaluation?.evaluation_method ||
                pipelineResult.before_evaluation?.evaluation_method}
            </p>
          )}

          {previewRows.length > 0 && (
            <div className="processed-preview">
              <div className="processed-preview__head">
                <h4>Processed data preview</h4>

                {pipelineResult.columns?.length > 8 && (
                  <span>Showing first 8 columns</span>
                )}
              </div>

              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      {previewColumns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {previewRows.map((row, idx) => (
                      <tr key={idx}>
                        {previewColumns.map((col) => (
                          <td key={col}>{String(row[col] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {pipelineResult.columns?.length > 8 && (
                <p className="text-muted" style={{ marginTop: "0.75rem" }}>
                  Download the CSV to view the complete processed dataset.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h3 className="card__title">Drop columns</h3>

        {Object.keys(plan.drop_columns || {}).length > 0 ? (
          <ul className="insight-list">
            {Object.entries(plan.drop_columns || {}).map(([col, info]) => (
              <li key={col}>
                <strong style={{ color: "var(--text)" }}>{col}</strong> —{" "}
                {info.reason}
              </li>
            ))}
          </ul>
        ) : (
          <p>No columns marked for dropping.</p>
        )}
      </div>

      <div className="card">
        <div className="imputation-head">
          <h3 className="card__title">Missing value imputation</h3>

          {imputationEntries.length > 0 && (
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={busyCol != null}
              onClick={resetAllImputation}
            >
              Reset all to recommended
            </button>
          )}
        </div>

        {planError && (
          <div className="alert alert--error" role="alert">
            {planError}
          </div>
        )}

        {imputationEntries.length > 0 ? (
          <ul className="imputation-list">
            {imputationEntries.map(([col, info]) => {
              const rec = info.recommended_method || info.method;
              const alts = info.alternatives || [rec];
              const options = [...new Set([rec, ...alts])];
              const isOverride = info.user_override || info.method !== rec;

              return (
                <li key={col} className="imputation-row">
                  <div className="imputation-row__col">
                    <span className="imputation-row__name">{col}</span>

                    {isOverride && (
                      <span className="imputation-row__badge">Custom</span>
                    )}
                  </div>

                  <div className="imputation-row__control">
                    <label className="visually-hidden" htmlFor={`imp-${col}`}>
                      Imputation for {col}
                    </label>

                    <select
                      id={`imp-${col}`}
                      className="select select--compact"
                      value={info.method}
                      disabled={busyCol != null}
                      onChange={(e) =>
                        handleImputationChange(col, e.target.value)
                      }
                    >
                      {options.map((m) => (
                        <option key={m} value={m}>
                          {m === rec
                            ? `${labelMethod(m)} (recommended)`
                            : labelMethod(m)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <p className="imputation-row__reason">{info.reason}</p>

                  {info.override_note && (
                    <p className="imputation-row__note">
                      {info.override_note}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p>No imputation required.</p>
        )}
      </div>

      <div className="card">
        <h3 className="card__title">Categorical encoding</h3>

        {Object.keys(plan.encoding || {}).length > 0 ? (
          <ul className="insight-list">
            {Object.entries(plan.encoding || {}).map(([col, info]) => (
              <li key={col}>
                <strong style={{ color: "var(--text)" }}>{col}</strong> —{" "}
                {info.method}{" "}
                <span style={{ color: "var(--text-dim)" }}>
                  ({info.reason})
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p>No categorical encoding required.</p>
        )}
      </div>

      <div className="card">
        <h3 className="card__title">Skewness correction / Transformations</h3>

        {Object.keys(plan.transformation || {}).length > 0 ? (
          <ul className="insight-list">
            {Object.entries(plan.transformation || {}).map(([col, info]) => (
              <li key={col}>
                <strong style={{ color: "var(--text)" }}>{col}</strong> —{" "}
                {info.method}{" "}
                <span style={{ color: "var(--text-dim)" }}>
                  ({info.reason})
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p>No skewness correction required.</p>
        )}
      </div>

      {plan.scaling && (
        <div className="card">
          <h3 className="card__title">Feature scaling</h3>
          <ul className="insight-list">
            <li>
              <strong style={{ color: "var(--text)" }}>
                {plan.scaling.method}
              </strong>{" "}
              — {plan.scaling.reason}
            </li>
          </ul>
        </div>
      )}

      {plan.feature_selection && (
        <div className="card">
          <h3 className="card__title">Feature selection</h3>
          <ul className="insight-list">
            <li>
              <strong style={{ color: "var(--text)" }}>
                {plan.feature_selection.method}
              </strong>{" "}
              — {plan.feature_selection.reason}
            </li>
          </ul>
        </div>
      )}

      {plan.outlier_handling && (
        <div className="card">
          <h3 className="card__title">Outlier handling</h3>
          <ul className="insight-list">
            <li>
              <strong style={{ color: "var(--text)" }}>
                {plan.outlier_handling.method}
              </strong>{" "}
              — {plan.outlier_handling.reason}
            </li>
          </ul>
        </div>
      )}
    </section>
  );
}

export default PreprocessingPlan;