import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";

const ACTION_LABELS = {
  login: "Signed in",
  logout: "Signed out",
  register: "Registered",
  dataset_analyzed: "Dataset analyzed",
  eda_completed: "EDA completed",
  visualizations_opened: "Visualizations opened",
  imputation_customized: "Imputation customized",
};

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ActivityPage() {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/activity", { params: { limit: 200 } });
        if (!cancelled) setItems(data);
      } catch (e) {
        if (!cancelled) {
          setError(e.response?.data?.detail || "Could not load activity.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <main className="page page--empty">
        <h1 className="page__title">Activity</h1>
        <p className="page__subtitle">Sign in to see your saved timeline.</p>
        <Link
          to="/login"
          className="btn btn--primary"
          state={{ from: { pathname: "/activity" } }}
        >
          Sign in
        </Link>
      </main>
    );
  }

  return (
    <main className="page page--activity">
      <header className="page__intro">
        <h1 className="page__title">Your activity</h1>
        <p className="page__subtitle">
          Recent actions recorded while you were signed in. Logging runs only when you are
          authenticated.
        </p>
      </header>

      {loading && <p className="text-muted">Loading…</p>}
      {error && (
        <div className="alert alert--error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="card">
          <p>No activity yet. Analyze a dataset or run EDA while signed in.</p>
          <Link to="/analyze" className="btn btn--primary" style={{ marginTop: "0.75rem" }}>
            Go to Analyze
          </Link>
        </div>
      )}

      {!loading && items.length > 0 && (
        <ul className="activity-list">
          {items.map((row) => (
            <li key={row.id} className="activity-item card">
              <div className="activity-item__top">
                <span className="activity-item__action">
                  {ACTION_LABELS[row.action] || row.action}
                </span>
                <time className="activity-item__time" dateTime={row.created_at}>
                  {formatTime(row.created_at)}
                </time>
              </div>
              {row.detail && Object.keys(row.detail).length > 0 && (
                <pre className="activity-item__detail">
                  {JSON.stringify(row.detail, null, 2)}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default ActivityPage;
