import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";
import WarningModal from "./WarningModal";

const TASK_LABELS = {
  binary_classification: "Binary classification",
  multiclass_classification: "Multiclass classification",
  regression: "Regression",
  unsupervised: "Unsupervised",
  needs_user_confirmation: "Needs confirmation (auto)",
};

function taskLabel(key) {
  return TASK_LABELS[key] || key || "—";
}

function shouldWarnTarget(selectedTarget, suggestedTargets, data) {
  const conf = data.target_confidence ?? data.confidence;
  const score = data.target_score;
  if (conf === "Weak target candidate") return true;
  if (typeof score === "number" && score < 4) return true;
  if (suggestedTargets?.length && !suggestedTargets.includes(selectedTarget)) return true;
  return false;
}

function shouldWarnTask(chosenTask, autoInferred) {
  if (!autoInferred || autoInferred === "needs_user_confirmation") return false;
  return chosenTask !== autoInferred;
}

function DecisionPanel({ variant = "default" }) {
  const navigate = useNavigate();
  const { logActivity } = useAuth();
  const {
    file,
    datasetDecision,
    setEdaSummary,
    setPreprocessingPlan,
    setDashboardPayload,
    setInsights,
    setDatasetQuality,
    setPipelineParams,
  } = useAnalysis();

  const [target, setTarget] = useState("");
  const [task, setTask] = useState("");
  const [model, setModel] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [reasons, setReasons] = useState([]);
  const [modelReasons, setModelReasons] = useState([]);
  const [secondaryModel, setSecondaryModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [vizLoading, setVizLoading] = useState(false);
  const [error, setError] = useState(null);
  const [autoInferredTask, setAutoInferredTask] = useState(null);

  const [targetWarning, setTargetWarning] = useState(null);
  const [taskWarning, setTaskWarning] = useState(null);

  useEffect(() => {
    if (datasetDecision) {
      setTarget(datasetDecision.selected_target || "");
      setTask(datasetDecision.inferred_task || "");
      setModel(datasetDecision.model_family_recommendation?.primary || "");
      setSecondaryModel(datasetDecision.model_family_recommendation?.secondary || "");
      setModelReasons(datasetDecision.model_family_recommendation?.reasons || []);
      setConfidence(datasetDecision.target_confidence ?? null);
      setReasons(datasetDecision.target_reasons || []);
      setAutoInferredTask(
        datasetDecision.auto_inferred_task ?? datasetDecision.inferred_task ?? null
      );
      setError(null);
      setTargetWarning(null);
      setTaskWarning(null);
    }
  }, [datasetDecision]);

  if (!datasetDecision) {
    const inner = (
      <div className="decision-placeholder card">
        <h3 className="card__title">Model decision</h3>
        <p>
          Upload a CSV in the sidebar and run <strong>Analyze dataset</strong> to unlock target
          detection, task inference, and model recommendations.
        </p>
      </div>
    );
    return variant === "centered" ? (
      <div className="decision-hero decision-hero--empty">{inner}</div>
    ) : (
      inner
    );
  }

  const recomputeDecision = async (targetValue, taskValue) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_col", targetValue);
    formData.append("task_type", taskValue || "");

    const response = await api.post("/recompute-decision", formData);
    const data = response.data;

    if (data.inferred_task && !taskValue) {
      setTask(data.inferred_task);
    }

    if (data.model_family_recommendation?.primary) {
      setModel(data.model_family_recommendation.primary);
      setSecondaryModel(data.model_family_recommendation.secondary);
      setModelReasons(data.model_family_recommendation.reasons || []);
    }

    setConfidence(data.target_confidence ?? data.confidence ?? null);
    setReasons(data.target_reasons ?? data.reasons ?? []);
    setAutoInferredTask(data.auto_inferred_task ?? data.inferred_task ?? null);

    return data;
  };

  const suggestedTargets = datasetDecision.target_candidates || [];
  const allColumns = datasetDecision.dataset_summary?.columns || [];

  const handleTargetChange = async (e) => {
    const newTarget = e.target.value;
    const previous = target;
    setTarget(newTarget);
    try {
      setError(null);
      const data = await recomputeDecision(newTarget, "");
      if (shouldWarnTarget(newTarget, suggestedTargets, data)) {
        setTargetWarning({
          open: true,
          newTarget,
          previousTarget: previous,
          data,
        });
      } else {
        setTargetWarning(null);
      }
    } catch (err) {
      console.error(err);
      setError("Could not update target. Check the API connection.");
      setTarget(previous);
    }
  };

  const confirmTargetWarning = () => {
    setTargetWarning(null);
  };

  const revertTargetWarning = async () => {
    const prev = targetWarning?.previousTarget;
    if (prev == null) {
      setTargetWarning(null);
      return;
    }
    setTarget(prev);
    try {
      await recomputeDecision(prev, "");
    } catch (err) {
      console.error(err);
    }
    setTargetWarning(null);
  };

  const handleTaskChange = async (e) => {
    const newTask = e.target.value;
    const previous = task;
    setTask(newTask);
    try {
      setError(null);
      const data = await recomputeDecision(target, newTask);
      const auto = data.auto_inferred_task;
      if (shouldWarnTask(newTask, auto)) {
        setTaskWarning({
          open: true,
          chosen: newTask,
          auto,
          previousTask: previous,
        });
      } else {
        setTaskWarning(null);
      }
    } catch (err) {
      console.error(err);
      setError("Could not update task type.");
      setTask(previous);
    }
  };

  const confirmTaskWarning = () => {
    setTaskWarning(null);
  };

  const applyAutoInferredTask = async () => {
    const auto = taskWarning?.auto;
    if (auto == null) {
      setTaskWarning(null);
      return;
    }
    setTask(auto);
    try {
      await recomputeDecision(target, auto);
    } catch (err) {
      console.error(err);
    }
    setTaskWarning(null);
  };

  const runEda = async () => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_col", target);

    setLoading(true);
    setError(null);

    try {
      const edaResponse = await api.post("/run-eda", formData);

      setEdaSummary(edaResponse.data.eda_summary);
      setInsights(edaResponse.data.insights);
      setDatasetQuality(edaResponse.data.dataset_quality);

      setPipelineParams({ target, task, model });

      formData.append("task_type", task);
      formData.append("model_family", model);
      formData.append("imputation_overrides", "{}");

      const planResponse = await api.post("/generate-preprocessing-plan", formData);

      setPreprocessingPlan(planResponse.data);
      void logActivity("eda_completed", {
        target,
        task,
        model_family: model,
        quality_score: edaResponse.data.dataset_quality?.quality_score,
        n_rows: edaResponse.data.eda_summary?.n_rows,
      });
      navigate("/results");
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          "EDA or preprocessing plan failed. Verify the backend and target column."
      );
    } finally {
      setLoading(false);
    }
  };

  const openDashboard = async () => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_col", target);

    setVizLoading(true);
    setError(null);

    try {
      const response = await api.post("/dashboard-data", formData);
      if (response.data?.error) {
        setError(response.data.error);
        return;
      }
      setDashboardPayload(response.data);
      void logActivity("visualizations_opened", { target });
      navigate("/visualize");
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          "Could not load the interactive dashboard. Is the API running?"
      );
    } finally {
      setVizLoading(false);
    }
  };

  const targetDetail =
    targetWarning?.data &&
    (targetWarning.data.target_reasons ?? targetWarning.data.reasons)?.length ? (
      <ul className="modal-list">
        {(targetWarning.data.target_reasons ?? targetWarning.data.reasons).map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    ) : null;

  const panelClass = variant === "centered" ? "decision-panel decision-panel--centered" : "decision-panel";

  return (
    <>
      <section className={variant === "centered" ? "section section--decision" : "section"}>
        <div className={variant === "centered" ? "decision-hero" : undefined}>
          <div className={panelClass}>
            <h2 className="decision-panel__title">Model decision</h2>
            <p className="decision-panel__lead">
              Target detection and task type drive the recommended model family. Adjust either
              field — we will warn you when a choice looks risky or out of line with auto-detection.
            </p>

            <div className="field field--large">
              <label className="label" htmlFor="target-select">
                Target variable
              </label>
              <select
                id="target-select"
                className="select select--large"
                value={target}
                onChange={handleTargetChange}
              >
                <optgroup label="Suggested targets">
                  {suggestedTargets.length === 0 && (
                    <option value="" disabled>
                      No auto-suggestions — pick from all columns
                    </option>
                  )}
                  {suggestedTargets.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </optgroup>
                {allColumns.length > 0 && (
                  <optgroup label="All columns">
                    {allColumns
                      .filter((c) => !suggestedTargets.includes(c))
                      .map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                  </optgroup>
                )}
              </select>
            </div>

            {autoInferredTask && (
              <p className="decision-meta">
                Auto-detected task from this target:{" "}
                <strong>{taskLabel(autoInferredTask)}</strong>
              </p>
            )}

            {confidence != null && confidence !== "" && (
              <div className="card card--inset">
                <h3 className="card__title">Target rationale</h3>
                <p>
                  <strong style={{ color: "var(--text)" }}>Confidence:</strong> {confidence}
                </p>
                {reasons.length > 0 && (
                  <>
                    <p style={{ marginTop: "0.75rem" }}>
                      <strong style={{ color: "var(--text)" }}>Signals</strong>
                    </p>
                    <ul className="insight-list">
                      {reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            <div className="card card--inset card--accent">
              <h3 className="card__title">Model recommendation</h3>
              <p className="decision-models">
                <span className="decision-models__primary">{model || "—"}</span>
                <span className="decision-models__sep">/</span>
                <span className="decision-models__secondary">{secondaryModel || "—"}</span>
              </p>
              {modelReasons.length > 0 && (
                <>
                  <p style={{ marginTop: "0.75rem" }}>
                    <strong style={{ color: "var(--text)" }}>Reasoning</strong>
                  </p>
                  <ul className="insight-list">
                    {modelReasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>

            <div className="field field--large">
              <label className="label" htmlFor="task-select">
                Task type
              </label>
              <select
                id="task-select"
                className="select select--large"
                value={task}
                onChange={handleTaskChange}
              >
                <option value="binary_classification">Binary classification</option>
                <option value="multiclass_classification">Multiclass classification</option>
                <option value="regression">Regression</option>
                <option value="unsupervised">Unsupervised</option>
              </select>
            </div>

            {error && (
              <div className="alert alert--error" role="alert">
                {error}
              </div>
            )}

            <div className="btn-group decision-actions">
              <button
                type="button"
                className="btn btn--primary btn--large"
                onClick={runEda}
                disabled={loading || vizLoading}
              >
                {loading ? "Running EDA…" : "Confirm & run EDA"}
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--large"
                onClick={openDashboard}
                disabled={loading || vizLoading}
              >
                {vizLoading ? "Building dashboard…" : "Open visualizations"}
              </button>
            </div>
          </div>
        </div>
      </section>

      <WarningModal
        open={Boolean(targetWarning?.open)}
        title="Target may be non-ideal"
        message="This target is outside the suggested list, scored weakly, or looks like a poor label column. Continuing is allowed, but metrics and models may be misleading."
        detail={targetDetail}
        primaryLabel="Keep this target"
        secondaryLabel="Revert to previous"
        onPrimary={confirmTargetWarning}
        onSecondary={revertTargetWarning}
      />

      <WarningModal
        open={Boolean(taskWarning?.open)}
        title="Task type differs from auto-detection"
        message={`The platform inferred ${taskLabel(taskWarning?.auto)} for this target, but you selected ${taskLabel(taskWarning?.chosen)}. That mismatch can produce the wrong metrics or model family.`}
        primaryLabel="Keep my task choice"
        secondaryLabel={
          taskWarning?.auto ? `Use ${taskLabel(taskWarning.auto)}` : "Match auto-detect"
        }
        onPrimary={confirmTaskWarning}
        onSecondary={applyAutoInferredTask}
      />
    </>
  );
}

export default DecisionPanel;
