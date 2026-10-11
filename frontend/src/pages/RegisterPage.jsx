import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const STEPS = { EMAIL: 1, CODE: 2, PASSWORD: 3 };

function RegisterPage() {
  const { requestSignupOtp, verifySignupOtp, completeSignup } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(STEPS.EMAIL);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [signupToken, setSignupToken] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const sendOtp = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await requestSignupOtp(email.trim());
      setStep(STEPS.CODE);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Could not send code. Check the API and email settings.");
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await verifySignupOtp(email.trim(), code.trim());
      setSignupToken(token);
      setStep(STEPS.PASSWORD);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Invalid or expired code.");
    } finally {
      setLoading(false);
    }
  };

  const finish = async (e) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== password2) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await completeSignup(signupToken, password);
      navigate("/analyze", { replace: true });
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Could not create account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <h1 className="auth-card__title">Create account</h1>
        <p className="auth-card__lead">
          {step === STEPS.EMAIL && "Enter your email — we’ll send a one-time code."}
          {step === STEPS.CODE && "Enter the 6-digit code from your inbox."}
          {step === STEPS.PASSWORD && "Choose a password for your account."}
        </p>

        {step === STEPS.EMAIL && (
          <form onSubmit={sendOtp} className="auth-form">
            <div className="field">
              <label className="label" htmlFor="reg-email">
                Email
              </label>
              <input
                id="reg-email"
                type="email"
                className="input"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            {error && (
              <div className="alert alert--error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
              {loading ? "Sending…" : "Send verification code"}
            </button>
          </form>
        )}

        {step === STEPS.CODE && (
          <form onSubmit={verifyOtp} className="auth-form">
            <p className="auth-step-hint">
              Code sent to <strong>{email}</strong>
            </p>
            <div className="field">
              <label className="label" htmlFor="reg-code">
                Verification code
              </label>
              <input
                id="reg-code"
                className="input input--otp"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                pattern="\d{6}"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                required
              />
            </div>
            {error && (
              <div className="alert alert--error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
              {loading ? "Checking…" : "Verify code"}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--block"
              onClick={() => {
                setStep(STEPS.EMAIL);
                setCode("");
                setError(null);
              }}
            >
              Use a different email
            </button>
          </form>
        )}

        {step === STEPS.PASSWORD && (
          <form onSubmit={finish} className="auth-form">
            <div className="field">
              <label className="label" htmlFor="reg-pass">
                Password
              </label>
              <input
                id="reg-pass"
                type="password"
                className="input"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="field">
              <label className="label" htmlFor="reg-pass2">
                Confirm password
              </label>
              <input
                id="reg-pass2"
                type="password"
                className="input"
                autoComplete="new-password"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && (
              <div className="alert alert--error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
              {loading ? "Creating…" : "Create account"}
            </button>
          </form>
        )}

        <p className="auth-card__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
        <p className="auth-card__footer">
          <Link to="/">Back to home</Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
