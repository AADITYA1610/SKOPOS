from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.json_cleaner import clean_for_json


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _finite(x: float) -> float:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return 0.0
    return float(x)


def _smart_num(val: float) -> str:
    if val != val or math.isinf(val):
        return "0"
    abs_val = abs(val)

    if abs_val >= 1_000_000:
        return f"{val / 1_000_000:.2g}M"
    if abs_val >= 1_000:
        return f"{val / 1_000:.2g}K"
    if abs_val >= 1:
        return f"{val:.2f}"
    return f"{val:.3f}"


def _bin_label(lo: float, hi: float) -> str:
    return f"{_smart_num(lo)} – {_smart_num(hi)}"


# ─────────────────────────────────────────────────────────────
# Row-level computation
# ─────────────────────────────────────────────────────────────

def _make_histogram(df: pd.DataFrame, col: str, max_bins: int = 20):
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) < 2:
        return []

    bins = min(max_bins, max(8, int(np.sqrt(len(s)))))
    counts, edges = np.histogram(s, bins=bins)

    return [
        {
            "label": _bin_label(edges[i], edges[i + 1]),
            "value": int(counts[i]),
        }
        for i in range(len(counts))
        if counts[i] > 0
    ]


def _pearson(df, a, b):
    s1 = pd.to_numeric(df[a], errors="coerce")
    s2 = pd.to_numeric(df[b], errors="coerce")
    valid = s1.notna() & s2.notna()

    if valid.sum() < 5:
        return None

    r = s1[valid].corr(s2[valid])
    return None if r != r else float(r)


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION (FIXED)
# ─────────────────────────────────────────────────────────────

def build_dashboard_payload(
    df: pd.DataFrame,
    target: str,
    eda_summary: dict | None = None,
    user_charts: list | None = None,
) -> dict:

    if target not in df.columns:
        return {"error": "Invalid target column"}

    user_charts = user_charts or []
    eda_summary = eda_summary or {}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target in numeric_cols:
        numeric_cols.remove(target)

    cat_cols = [c for c in df.columns if c not in numeric_cols]

    panels = []

    # ── Target distribution ──
    if pd.api.types.is_numeric_dtype(df[target]):
        panels.append({
            "id": "target_dist",
            "title": f"{target} Distribution",
            "chart": "histogram",
            "data": _make_histogram(df, target),
        })
    else:
        vc = df[target].astype(str).value_counts()
        panels.append({
            "id": "target_dist",
            "title": f"{target} Distribution",
            "chart": "bar",
            "data": [{"name": k, "value": int(v)} for k, v in vc.items()],
        })

    # ── Top correlations (safe) ──
    if pd.api.types.is_numeric_dtype(df[target]):
        cors = []
        for col in numeric_cols[:15]:
            r = _pearson(df, target, col)
            if r is not None:
                cors.append({"name": col, "value": r})

        if cors:
            panels.append({
                "id": "correlation",
                "title": f"Correlation with {target}",
                "chart": "bar",
                "data": cors,
            })

    # ── Feature distributions ──
    for col in numeric_cols[:2]:
        panels.append({
            "id": f"dist_{col}",
            "title": col,
            "chart": "histogram",
            "data": _make_histogram(df, col),
        })

    # ── USER CHARTS (FIXED SAFE MERGE) ──
    for ch in user_charts:
        if isinstance(ch, dict):
            panels.append(ch)

    return clean_for_json({
        "meta": {
            "target": target,
            "rows": len(df),
            "cols": len(df.columns),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
        "panels": panels,
    })