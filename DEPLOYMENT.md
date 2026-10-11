# Deploying TADAA (API + frontend) and using the cloud for data

This document summarizes how **email + OTP auth** is configured, how to **deploy** the stack, and how to move **persistent data** off a single server disk into managed cloud services.

## 1. Email + OTP (how it works)

1. **Request code** — `POST /auth/signup/request-otp` with `{ "email": "..." }`  
   - Creates a short-lived row in `email_otps`, hashes the 6-digit code, sends mail.
2. **Verify code** — `POST /auth/signup/verify-otp` with `{ "email", "code" }`  
   - Returns a **signup JWT** (`signup_token`, ~15 minutes).
3. **Set password** — `POST /auth/signup/complete` with `{ "signup_token", "password" }`  
   - Creates the user and returns a normal **session JWT**.

### Configure outbound email (production)

Pick **one** path:

| Method | Environment variables |
|--------|------------------------|
| **Resend** (simple HTTP API) | `RESEND_API_KEY`, `RESEND_FROM` (e.g. `TADAA <onboarding@resend.dev>` or your verified domain) |
| **SMTP** (Gmail, SendGrid SMTP, etc.) | `SMTP_HOST`, `SMTP_PORT` (usually `587`), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| **Local dev only** | `TADAA_DEV_LOG_OTP=1` — prints the OTP in the API process **stdout** (never enable this in production) |

If none of these are set, `request-otp` returns **503** with a clear message.

### Other secrets

- **`TADAA_JWT_SECRET`** — long random string; required in production for JWT signing.
- **`CORS_ALLOW_ORIGINS`** — comma-separated list, e.g. `https://app.example.com,http://localhost:5173`.

### Frontend

- Build with **`VITE_API_URL=https://api.yourdomain.com`** so the browser calls your deployed API.

---

## 2. How to deploy this kind of app

Typical split:

| Piece | Role | Common options |
|-------|------|----------------|
| **Frontend** | Static SPA after `npm run build` | Vercel, Netlify, Cloudflare Pages, S3 + CloudFront, Azure Static Web Apps |
| **Backend** | FastAPI + Uvicorn | Railway, Render, Fly.io, Google Cloud Run, AWS ECS/Fargate, Azure Container Apps, a VPS + Docker |
| **Process** | One container or one process | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

**Checklist**

1. Set env vars on the host (`TADAA_JWT_SECRET`, email provider, `CORS_ALLOW_ORIGINS`, `VITE_API_URL` at build time for the frontend).
2. Expose HTTPS for the API; point the SPA’s `VITE_API_URL` at that URL.
3. Health check: `GET /` on the API.

---

## 3. Saving data “in the cloud”

Today, **users, OTP rows, and activity** live in **SQLite** at `backend/data/tadaa.db` on the API server. That is fine for a single instance and demos; for production you usually want:

### A. Managed relational database (recommended for users + activity)

- **Neon**, **Supabase (Postgres)**, **PlanetScale (MySQL)**, **AWS RDS**, **Azure Database for PostgreSQL**, etc.
- Point the app at **`DATABASE_URL`** (or split host/user/password) and replace raw `sqlite3` usage with:
  - **SQLAlchemy 2.x** + Alembic migrations, or
  - **`psycopg`** (Postgres) with parameterized queries.

**Migration path:** export SQLite → import into Postgres, or run a one-off script; then ship code that talks to Postgres only in production (`if os.getenv("DATABASE_URL")` …).

### B. Object storage for uploaded CSVs (optional next step)

- **S3**, **GCS**, **Azure Blob**, **R2**, etc.
- Flow: upload file → store blob under `user_id/session_id/...` → pass a **presigned URL** or server-side path into existing pandas logic instead of only keeping files in memory.

### C. Multi-instance APIs

- If you run **more than one** API replica, **do not** rely on SQLite on local disk (each instance has its own file). Use **Postgres** (or another shared DB) and optionally **Redis** for OTP rate limits / ephemeral OTP storage.

---

## 4. Quick local dev with OTP

```bash
set TADAA_DEV_LOG_OTP=1
uvicorn main:app --reload --app-dir backend
```

Watch the terminal for `[TADAA DEV OTP] to=... code=...` when you register.

---

## 5. Security notes

- Use **HTTPS** everywhere in production.
- Rotate **`TADAA_JWT_SECRET`** if leaked; all sessions invalidate.
- Restrict **CORS** to your real frontend origin(s).
- For Resend/SMTP, use **domain verification** and SPF/DKIM as your provider requires.
