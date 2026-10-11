import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({ baseURL: API_BASE });

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    localStorage.setItem("tadaa_token", token);
  } else {
    delete api.defaults.headers.common.Authorization;
    localStorage.removeItem("tadaa_token");
  }
}

/** Restore Authorization header from localStorage (call on app load). */
export function initApiAuth() {
  const t = localStorage.getItem("tadaa_token");
  if (t) {
    api.defaults.headers.common.Authorization = `Bearer ${t}`;
  }
  return t || null;
}
