"""
Users, JWT auth, email + OTP signup, activity log (SQLite by default).

JWT payload uses "ident" (email or legacy username). Old tokens with "username" still work.
"""
from __future__ import annotations

import json
import os
import sqlite3
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from src.email_send import EmailNotConfiguredError, send_otp_email

SECRET_KEY = os.environ.get("TADAA_JWT_SECRET", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
SIGNUP_TOKEN_EXPIRE_MINUTES = 15
OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tadaa.db"

auth_router = APIRouter(prefix="/auth", tags=["auth"])
activity_router = APIRouter(prefix="/activity", tags=["activity"])
security = HTTPBearer()


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_users(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}
    if "email" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "email_verified" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1"
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
        ON users(email) WHERE email IS NOT NULL
        """
    )


def init_auth_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _migrate_users(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code_hash BLOB NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


class UserCreateLegacy(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Email for new accounts; legacy username-only accounts may use username here."""

    email: str = Field(..., min_length=1, max_length=320)
    password: str


class OtpSendIn(BaseModel):
    email: EmailStr


class OtpVerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class SignupCompleteIn(BaseModel):
    signup_token: str
    password: str = Field(..., min_length=8, max_length=128)


class OtpVerifyOut(BaseModel):
    signup_token: str
    expires_in_minutes: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: Optional[str] = None
    username: Optional[str] = None


class ActivityIn(BaseModel):
    action: str = Field(..., min_length=1, max_length=120)
    detail: dict[str, Any] = Field(default_factory=dict)


class ActivityOut(BaseModel):
    id: int
    action: str
    detail: dict[str, Any]
    created_at: str


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def create_access_token(user_id: int, ident: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "ident": ident,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_signup_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=SIGNUP_TOKEN_EXPIRE_MINUTES)
    payload = {
        "typ": "signup",
        "email": email.lower(),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserOut:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("typ") == "signup":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Use a session token, not a signup token",
            )
        uid = int(payload.get("sub", 0))
        ident = payload.get("ident") or payload.get("username")
        if not uid or not ident:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE id = ?", (uid,)
        ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return UserOut(
        id=row["id"],
        email=row["email"],
        username=row["username"],
    )


def _find_user_by_login(conn: sqlite3.Connection, login: str) -> Optional[sqlite3.Row]:
    key = login.strip().lower()
    return conn.execute(
        """
        SELECT id, username, email, password_hash FROM users
        WHERE LOWER(COALESCE(email, '')) = ? OR LOWER(username) = ?
        """,
        (key, key),
    ).fetchone()


@auth_router.post("/register", response_model=TokenOut)
def register_legacy(body: UserCreateLegacy):
    """Legacy username + password (no email). Prefer /auth/signup/* for new accounts."""
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = _hash_password(body.password)
    try:
        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, created_at, email, email_verified)
                VALUES (?, ?, ?, NULL, 1)
                """,
                (body.username.lower(), pw_hash, now),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    token = create_access_token(user_id, body.username.lower())
    return TokenOut(access_token=token)


@auth_router.post("/signup/request-otp")
def signup_request_otp(body: OtpSendIn):
    email = body.email.lower()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with get_db() as conn:
        existing = conn.execute(
            """
            SELECT id FROM users
            WHERE LOWER(COALESCE(email,'')) = ? OR LOWER(username) = ?
            """,
            (email, email),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Sign in instead.",
            )

        conn.execute("DELETE FROM email_otps WHERE LOWER(email) = ?", (email,))

        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt())
        exp = (now + timedelta(minutes=OTP_EXPIRE_MINUTES)).isoformat()
        conn.execute(
            """
            INSERT INTO email_otps (email, code_hash, expires_at, attempts, created_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (email, code_hash, exp, now_iso),
        )

    try:
        send_otp_email(body.email, code)
    except EmailNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not send email: {e!s}",
        ) from e

    return {"ok": True, "message": "If this email is available, a code was sent."}


@auth_router.post("/signup/verify-otp", response_model=OtpVerifyOut)
def signup_verify_otp(body: OtpVerifyIn):
    email = body.email.lower()
    now = datetime.now(timezone.utc)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, code_hash, expires_at, attempts FROM email_otps
            WHERE LOWER(email) = ?
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification code for this email. Request a new code.",
            )

        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            conn.execute("DELETE FROM email_otps WHERE id = ?", (row["id"],))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Request a new code.",
            )

        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            conn.execute("DELETE FROM email_otps WHERE id = ?", (row["id"],))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code expired. Request a new one.",
            )

        if not bcrypt.checkpw(body.code.encode("utf-8"), row["code_hash"]):
            conn.execute(
                "UPDATE email_otps SET attempts = attempts + 1 WHERE id = ?",
                (row["id"],),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code.",
            )

        conn.execute("DELETE FROM email_otps WHERE id = ?", (row["id"],))

    token = create_signup_token(email)
    return OtpVerifyOut(
        signup_token=token,
        expires_in_minutes=SIGNUP_TOKEN_EXPIRE_MINUTES,
    )


@auth_router.post("/signup/complete", response_model=TokenOut)
def signup_complete(body: SignupCompleteIn):
    try:
        payload = decode_token(body.signup_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired signup token. Verify the OTP again.",
        )
    if payload.get("typ") != "signup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signup token",
        )
    email = payload.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Invalid signup token payload")

    now = datetime.now(timezone.utc).isoformat()
    pw_hash = _hash_password(body.password)
    # username column must remain NOT NULL: use email as stable username
    uname = email

    try:
        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, created_at, email, email_verified)
                VALUES (?, ?, ?, ?, 1)
                """,
                (uname, pw_hash, now, email),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists. Sign in instead.",
        )

    token = create_access_token(user_id, email)
    return TokenOut(access_token=token)


@auth_router.post("/login", response_model=TokenOut)
def login(body: UserLogin):
    key = body.email.lower()
    with get_db() as conn:
        row = _find_user_by_login(conn, key)
    if not row or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    ident = row["email"] or row["username"]
    token = create_access_token(row["id"], ident)
    return TokenOut(access_token=token)


@auth_router.get("/me", response_model=UserOut)
async def me(user: UserOut = Depends(get_current_user)):
    return user


@activity_router.post("", response_model=ActivityOut)
def log_activity(
    body: ActivityIn,
    user: UserOut = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).isoformat()
    detail_json = json.dumps(body.detail)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO activities (user_id, action, detail, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user.id, body.action, detail_json, now),
        )
        aid = cur.lastrowid
        row = conn.execute(
            "SELECT id, action, detail, created_at FROM activities WHERE id = ?",
            (aid,),
        ).fetchone()
    detail = json.loads(row["detail"] or "{}")
    return ActivityOut(
        id=row["id"], action=row["action"], detail=detail, created_at=row["created_at"]
    )


@activity_router.get("", response_model=list[ActivityOut])
def list_activities(
    limit: int = 100,
    user: UserOut = Depends(get_current_user),
):
    limit = max(1, min(limit, 500))
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, action, detail, created_at FROM activities
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user.id, limit),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            ActivityOut(
                id=r["id"],
                action=r["action"],
                detail=json.loads(r["detail"] or "{}"),
                created_at=r["created_at"],
            )
        )
    return out
