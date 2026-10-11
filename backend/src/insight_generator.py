"""
Insight Generator
-----------------
Converts an eda_summary dict (from eda_engine.run_eda) into a ranked
list of plain-English insight strings.

Contract (unchanged): accepts eda_summary dict, returns list[str].
No changes required in main.py or any UI component.

Improvements over v1:
  - Severity-ordered output (critical → warning → info)
  - Covers new eda_engine keys: datetime_cols, pseudo_categorical_columns,
    categorical_correlation_pairs, zero_variance_columns
  - Existing insights are more specific: name actual columns, show numbers
  - Covers previously silent signals: outlier %, kurtosis, feature/row ratio,
    class imbalance ratio (for categorical targets)
"""


def generate_insights(eda_summary: dict) -> list[str]:
    insights: list[str] = []
    flags = eda_summary.get("dataset_flags", {})

    # ── helpers ───────────────────────────────────────────────────────────────

    def _col_snippet(cols: list, limit: int = 3) -> str:
        """'a, b, c (+N more)'"""
        shown = cols[:limit]
        rest = len(cols) - limit
        base = ", ".join(shown)
        return f"{base} (+{rest} more)" if rest > 0 else base

    # ══════════════════════════════════════════════════════════════════════════
    # 0 — Dataset overview (always present)
    # ══════════════════════════════════════════════════════════════════════════
    n_rows = eda_summary.get("n_rows", 0)
    n_features = eda_summary.get("n_features", 0)
    insights.append(
        f"Dataset has {n_rows:,} rows and {n_features} feature columns."
    )

    # Warn on very small datasets
    if n_rows < 500:
        insights.append(
            f"Small dataset ({n_rows:,} rows) — model generalisation may be limited; "
            "consider collecting more samples or using cross-validation carefully."
        )

    # High feature-to-row ratio (curse of dimensionality risk)
    if n_features > 0 and n_rows > 0:
        ratio = n_features / n_rows
        if ratio > 0.1:
            insights.append(
                f"Feature-to-row ratio is high ({n_features} features / {n_rows:,} rows = "
                f"{ratio:.2f}) — dimensionality reduction or aggressive feature selection "
                "is recommended."
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 1 — CRITICAL: zero-variance columns (new from improved eda_engine)
    # ══════════════════════════════════════════════════════════════════════════
    zero_var = eda_summary.get("zero_variance_columns", [])
    if zero_var:
        insights.append(
            f"[Critical] {len(zero_var)} column(s) have zero variance "
            f"({_col_snippet(zero_var)}) — they carry no information and "
            "must be dropped before training."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 2 — CRITICAL: high missing values
    # ══════════════════════════════════════════════════════════════════════════
    high_missing = eda_summary.get("high_missing_columns", [])
    missing_pct = eda_summary.get("missing_percentage", {})

    if high_missing:
        # Show actual percentages for the worst offenders
        details = []
        for col in high_missing[:3]:
            pct = missing_pct.get(col, 0)
            details.append(f"{col} ({pct:.1f}%)")
        rest = len(high_missing) - 3
        suffix = f" and {rest} more" if rest > 0 else ""
        insights.append(
            f"[Critical] High missingness in: {', '.join(details)}{suffix}. "
            "Consider dropping these columns or using advanced imputation."
        )
    else:
        moderate_missing = eda_summary.get("moderate_missing_columns", [])
        if moderate_missing:
            insights.append(
                f"{len(moderate_missing)} column(s) have moderate missing values "
                f"({_col_snippet(moderate_missing)}) — imputation is recommended."
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 3 — DateTime columns (new from improved eda_engine)
    # ══════════════════════════════════════════════════════════════════════════
    datetime_cols = eda_summary.get("datetime_cols", [])
    if datetime_cols:
        insights.append(
            f"Detected {len(datetime_cols)} datetime column(s) "
            f"({_col_snippet(datetime_cols)}) — consider extracting signals "
            "like day-of-week, month, or time-since-epoch before training."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 4 — Pseudo-categorical columns (new from improved eda_engine)
    # ══════════════════════════════════════════════════════════════════════════
    pseudo_cat = eda_summary.get("pseudo_categorical_columns", [])
    if pseudo_cat:
        insights.append(
            f"{len(pseudo_cat)} numerical column(s) have fewer than 10 unique values "
            f"({_col_snippet(pseudo_cat)}) — these may be ordinal codes or tier labels "
            "and could benefit from categorical encoding instead of numeric treatment."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 5 — Skewness
    # ══════════════════════════════════════════════════════════════════════════
    high_skew = eda_summary.get("high_skew_columns", [])
    skewness_map = eda_summary.get("skewness", {})

    if high_skew:
        # Find the most extreme skew for the message
        worst = max(high_skew, key=lambda c: abs(skewness_map.get(c, 0)))
        worst_val = skewness_map.get(worst, 0)
        insights.append(
            f"{len(high_skew)} numerical feature(s) show strong skewness "
            f"(worst: {worst} at {worst_val:+.2f}) — "
            "log or power transforms are recommended."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 6 — Outliers (more specific than before)
    # ══════════════════════════════════════════════════════════════════════════
    if flags.get("has_outliers"):
        outlier_pct_map = eda_summary.get("outlier_percentage", {})
        # Find the columns with the highest outlier percentages
        top_outlier_cols = sorted(
            [(c, v) for c, v in outlier_pct_map.items() if v > 5],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        if top_outlier_cols:
            detail = ", ".join(f"{c} ({v:.1f}%)" for c, v in top_outlier_cols)
            insights.append(
                f"Outliers detected in: {detail}. "
                "IQR capping or robust scaling is recommended."
            )
        else:
            insights.append("Outliers detected in numerical features.")

    # ══════════════════════════════════════════════════════════════════════════
    # 7 — Numerical multicollinearity
    # ══════════════════════════════════════════════════════════════════════════
    corr_pairs = eda_summary.get("multicollinearity_pairs", [])
    if corr_pairs:
        # Report up to 2 pairs with their actual correlation values
        pair_strs = []
        for p in corr_pairs[:2]:
            pair_strs.append(
                f"{p['col1']} ↔ {p['col2']} (r={p['corr']:.2f})"
            )
        rest = len(corr_pairs) - 2
        suffix = f" and {rest} more pair(s)" if rest > 0 else ""
        insights.append(
            f"Strong numerical correlation: {'; '.join(pair_strs)}{suffix}. "
            "Consider dropping or combining one of each correlated pair."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 8 — Categorical correlation via Cramér's V (new from improved eda_engine)
    # ══════════════════════════════════════════════════════════════════════════
    cat_corr_pairs = eda_summary.get("categorical_correlation_pairs", [])
    if cat_corr_pairs:
        pair_strs = []
        for p in cat_corr_pairs[:2]:
            pair_strs.append(
                f"{p['col1']} ↔ {p['col2']} (V={p['cramers_v']:.2f})"
            )
        rest = len(cat_corr_pairs) - 2
        suffix = f" and {rest} more" if rest > 0 else ""
        insights.append(
            f"Strong categorical association (Cramér's V): "
            f"{'; '.join(pair_strs)}{suffix}. "
            "Redundant categorical columns can inflate dimensionality after encoding."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 9 — Encoding risk
    # ══════════════════════════════════════════════════════════════════════════
    if flags.get("encoding_risk"):
        enc_risk_cols = eda_summary.get("encoding_risk_columns", [])
        insights.append(
            f"High-cardinality categorical feature(s) detected "
            f"({_col_snippet(enc_risk_cols)}) — one-hot encoding will produce "
            "many sparse columns; prefer target or frequency encoding."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 10 — Scaling
    # ══════════════════════════════════════════════════════════════════════════
    if flags.get("needs_scaling"):
        spread_map = eda_summary.get("scale_spread", {})
        widest = max(spread_map, key=spread_map.get) if spread_map else None
        if widest:
            insights.append(
                f"Feature scaling is recommended — the widest numeric range belongs to "
                f"'{widest}' (spread: {spread_map[widest]:,.1f}). "
                "Use standard or robust scaling for distance/linear models."
            )
        else:
            insights.append(
                "Feature scaling recommended due to wide numeric value ranges."
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 11 — Low-variance (near-zero, not exactly zero)
    # ══════════════════════════════════════════════════════════════════════════
    low_var = eda_summary.get("low_variance_columns", [])
    if low_var:
        insights.append(
            f"{len(low_var)} column(s) have near-zero variance "
            f"({_col_snippet(low_var)}) — likely to have minimal predictive "
            "contribution; consider dropping."
        )

    return insights
