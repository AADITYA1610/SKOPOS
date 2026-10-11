import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, initApiAuth, setAuthToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = initApiAuth();
    if (!token) {
      setUser(null);
      setReady(true);
      return;
    }
    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        setAuthToken(null);
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setAuthToken(data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
    try {
      await api.post("/activity", { action: "login", detail: {} });
    } catch {
      /* ignore */
    }
    return me.data;
  }, []);

  const requestSignupOtp = useCallback(async (email) => {
    await api.post("/auth/signup/request-otp", { email });
  }, []);

  const verifySignupOtp = useCallback(async (email, code) => {
    const { data } = await api.post("/auth/signup/verify-otp", { email, code });
    return data.signup_token;
  }, []);

  const completeSignup = useCallback(async (signupToken, password) => {
    const { data } = await api.post("/auth/signup/complete", {
      signup_token: signupToken,
      password,
    });
    setAuthToken(data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
    try {
      await api.post("/activity", {
        action: "register",
        detail: { email: me.data.email || me.data.username },
      });
    } catch {
      /* ignore */
    }
    return me.data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/activity", { action: "logout", detail: {} });
    } catch {
      /* ignore */
    }
    setAuthToken(null);
    setUser(null);
  }, []);

  const logActivity = useCallback(async (action, detail = {}) => {
    if (!localStorage.getItem("tadaa_token")) return;
    try {
      await api.post("/activity", { action, detail });
    } catch (e) {
      console.warn("Activity log failed:", e?.response?.data || e.message);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      isAuthenticated: Boolean(user),
      login,
      requestSignupOtp,
      verifySignupOtp,
      completeSignup,
      logout,
      logActivity,
    }),
    [
      user,
      ready,
      login,
      requestSignupOtp,
      verifySignupOtp,
      completeSignup,
      logout,
      logActivity,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
