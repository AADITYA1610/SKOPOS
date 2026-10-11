import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/analyze";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        "Could not sign in. Check your credentials and that the API is running.";
      setError(typeof msg === "string" ? msg : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <h1 className="auth-card__title">Sign in</h1>
        <p className="auth-card__lead">
          Use your TADAA account to save a timeline of what you do in the app (dataset runs, EDA,
          charts).
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="field">
            <label className="label" htmlFor="login-email">
              Email or username
            </label>
            <input
              id="login-email"
              type="text"
              className="input"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <p className="auth-inline-hint">
            Legacy accounts created with a username only can still sign in using that username in
            this field.
          </p>
          <div className="field">
            <label className="label" htmlFor="login-pass">
              Password
            </label>
            <input
              id="login-pass"
              type="password"
              className="input"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="alert alert--error" role="alert">
              {error}
            </div>
          )}

          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-card__footer">
          No account? <Link to="/register">Create one</Link>
        </p>
        <p className="auth-card__footer">
          <Link to="/">Back to home</Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
