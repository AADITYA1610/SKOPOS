import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import KlausChat from "./KlausChat";

function Layout() {
  const { edaSummary } = useAnalysis();
  const { user, ready, logout, isAuthenticated } = useAuth();
  const [klausOpen, setKlausOpen] = useState(false);

  return (
    <div className="app app--with-nav">
      <nav className="site-nav" aria-label="Main">
        <NavLink to="/" className="site-nav__brand">
          LOOM
        </NavLink>

        <div className="site-nav__links">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `site-nav__link${isActive ? " active" : ""}`}
          >
            Home
          </NavLink>

          <NavLink
            to="/analyze"
            className={({ isActive }) => `site-nav__link${isActive ? " active" : ""}`}
          >
            Analyze
          </NavLink>

          <NavLink
            to="/results"
            className={({ isActive }) =>
              `site-nav__link${isActive ? " active" : ""}${
                !edaSummary ? " site-nav__link--muted" : ""
              }`
            }
            aria-disabled={!edaSummary}
            onClick={(e) => {
              if (!edaSummary) e.preventDefault();
            }}
          >
            Results
          </NavLink>

          <NavLink
            to="/visualize"
            className={({ isActive }) => `site-nav__link${isActive ? " active" : ""}`}
          >
            Visualize
          </NavLink>

          <NavLink
            to="/activity"
            className={({ isActive }) => `site-nav__link${isActive ? " active" : ""}`}
          >
            Activity
          </NavLink>
        </div>

        <div className="site-nav__auth">
          {!ready ? (
            <span className="site-nav__user site-nav__user--muted">…</span>
          ) : isAuthenticated ? (
            <>
              <span className="site-nav__user" title={user.email || user.username}>
                {user.email || user.username}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => logout()}
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="site-nav__link site-nav__link--cta">
                Sign in
              </Link>
              <Link to="/register" className="btn btn--primary btn--small">
                Register
              </Link>
            </>
          )}
        </div>
      </nav>

      <Outlet />

      <aside
        className={`klaus-panel${klausOpen ? " klaus-panel--open" : ""}`}
        aria-label="Klaus visualization assistant"
        aria-hidden={!klausOpen}
      >
        <div className="klaus-panel__inner">
          <div className="klaus-panel__topbar">
            <div className="klaus-panel__topbar-title">
              <span aria-hidden="true">🧐</span>
              <span>Ask Klaus</span>
              <span className="badge badge--medium" style={{ fontSize: "0.65rem" }}>
                AI
              </span>
            </div>

            <button
              type="button"
              className="btn btn--ghost btn--small"
              aria-label="Close Klaus panel"
              onClick={() => setKlausOpen(false)}
            >
              ✕
            </button>
          </div>

          <div className="klaus-panel__body">
            {klausOpen && <KlausChat />}
          </div>
        </div>
      </aside>

      <button
        type="button"
        className={`klaus-fab${klausOpen ? " klaus-fab--active" : ""}`}
        aria-label={klausOpen ? "Close Klaus" : "Open Klaus visualization assistant"}
        aria-expanded={klausOpen}
        onClick={() => setKlausOpen((v) => !v)}
      >
        <span className="klaus-fab__icon" aria-hidden="true">
          {klausOpen ? "✕" : "🧐"}
        </span>
        <span className="klaus-fab__label">
          {klausOpen ? "Close" : "Ask Klaus"}
        </span>
      </button>
    </div>
  );
}

export default Layout;