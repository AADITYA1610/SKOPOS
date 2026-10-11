"""
EDA Signals Engine (Task-Agnostic)
----------------------------------
Generates structured dataset signals for:
- Preprocessing decision engine
- UI display layer
- Pipeline generation module

This is a rule-driven EDA layer (NOT AutoML).
It DOES NOT infer task type or model family.

Improvements (additive only — no existing keys changed):
  1. DateTime detection  → strips datetime cols before type split,
                           exposes `datetime_cols` in summary.
  2. Pseudo-categorical  → numerical cols with < 10 unique values
                           exposed as `pseudo_categorical_columns`.
  3. Cramér's V          → cross-type categorical correlation pairs
                           exposed as `categorical_correlation_pairs`.
  4. Zero-variance check → exact-zero variance cols exposed as
                           `zero_variance_columns`; flag added to
                           `dataset_flags["has_zero_variance"]`.
"""

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis, chi2_contingency


# ==========================================================
# Utility Functions
# ==========================================================

def detect_id_columns(df):
    return [col for col in df.columns if df[col].nunique() == len(df)]


# ----------------------------------------------------------
# NEW ① — DateTime detection
# ----------------------------------------------------------
def detect_datetime_columns(df, candidate_cols):
    """
    Returns columns that are either already datetime dtype or whose
    string values parse cleanly as dates (sampled for speed).
    """
    datetime_cols = []
    for col in candidate_cols:
        # Already a datetime dtype
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            datetime_cols.append(col)
            continue
        # Try to infer from object/string columns
        if df[col].dtype == object:
            sample = df[col].dropna().head(50)
            if len(sample) == 0:
                continue
            try:
                parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="raise")
                # Only flag if the vast majority parsed successfully
                datetime_cols.append(col)
            except Exception:
                pass
    return datetime_cols


def detect_column_types(df, feature_cols):
    numerical_cols = df[feature_cols].select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df[feature_cols].select_dtypes(exclude=np.number).columns.tolist()
    return numerical_cols, categorical_cols


# ----------------------------------------------------------
# NEW ② — Pseudo-categorical detection
# ----------------------------------------------------------
def detect_pseudo_categorical(df, numerical_cols, threshold=10):
    """
    Numerical columns with fewer than `threshold` unique values are
    likely ordinal codes or tier labels, not true continuous features.
    Returns a list of such column names.
    """
    return [
        col for col in numerical_cols
        if df[col].nunique(dropna=True) < threshold
    ]


def compute_missing_signals(df, feature_cols):
    missing_pct = (df[feature_cols].isnull().mean() * 100).round(2).to_dict()

    high_missing = [c for c, p in missing_pct.items() if p > 30]
    moderate_missing = [c for c, p in missing_pct.items() if 5 < p <= 30]

    return missing_pct, high_missing, moderate_missing


def compute_categorical_signals(df, categorical_cols):
    cardinality = {c: df[c].nunique() for c in categorical_cols}

    dominant_ratio = {}
    for col in categorical_cols:
        vc = df[col].value_counts(normalize=True, dropna=False)
        if len(vc) > 0:
            dominant_ratio[col] = round(float(vc.iloc[0] * 100), 2)
        else:
            dominant_ratio[col] = 0

    high_cardinality = [c for c, v in cardinality.items() if v > 10]

    encoding_risk = [
        c for c in categorical_cols
        if cardinality.get(c, 0) > 20 and dominant_ratio.get(c, 0) < 20
    ]

    return cardinality, dominant_ratio, high_cardinality, encoding_risk


def compute_numerical_signals(df, numerical_cols):

    skewness = {}
    kurtosis_vals = {}

    for col in numerical_cols:
        series = df[col].dropna()

        if len(series) > 0:
            val_skew = skew(series)
            val_kurt = kurtosis(series)

            if np.isnan(val_skew) or np.isinf(val_skew):
                val_skew = 0
            if np.isnan(val_kurt) or np.isinf(val_kurt):
                val_kurt = 0

            skewness[col] = round(float(val_skew), 3)
            kurtosis_vals[col] = round(float(val_kurt), 3)
        else:
            skewness[col] = 0
            kurtosis_vals[col] = 0

    high_skew = [c for c, v in skewness.items() if abs(v) > 1]

    def outlier_pct(series):
        if len(series) == 0:
            return 0

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            return 0

        mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
        return round(float(mask.mean() * 100), 2)

    outlier_percentage = {
        c: outlier_pct(df[c].dropna())
        for c in numerical_cols
    }

    # Safe variance
    variance_raw = df[numerical_cols].var().to_dict()
    variance = {}

    for col, val in variance_raw.items():
        if pd.isna(val) or np.isinf(val):
            variance[col] = 0
        else:
            variance[col] = round(float(val), 5)

    # ----------------------------------------------------------
    # NEW ④ — Zero-variance (exact) vs near-zero (< 0.01)
    # ----------------------------------------------------------
    zero_variance = [c for c, v in variance.items() if v == 0.0]
    low_variance = [c for c, v in variance.items() if 0.0 < v < 0.01]

    scale_spread = {}
    for col in numerical_cols:
        series = df[col].dropna()
        if len(series) > 0:
            spread = series.max() - series.min()

            if pd.isna(spread) or np.isinf(spread):
                spread = 0

            scale_spread[col] = float(round(spread, 2))
        else:
            scale_spread[col] = 0.0

    scaling_needed = any(v > 50 for v in scale_spread.values())

    return (
        skewness,
        kurtosis_vals,
        high_skew,
        outlier_percentage,
        variance,
        low_variance,
        zero_variance,       # ← new addition (position 7)
        scale_spread,
        scaling_needed
    )


def compute_correlation_signals(df, numerical_cols):

    if len(numerical_cols) == 0:
        return [], 0

    corr_matrix = df[numerical_cols].corr()

    high_corr_pairs = []

    for i in range(len(corr_matrix.columns)):
        for j in range(i):
            val = corr_matrix.iloc[i, j]

            if pd.isna(val) or np.isinf(val):
                continue

            if abs(val) > 0.75:
                high_corr_pairs.append({
                    "col1": corr_matrix.columns[i],
                    "col2": corr_matrix.columns[j],
                    "corr": round(float(val), 2)
                })

    return high_corr_pairs, len(high_corr_pairs)


# ----------------------------------------------------------
# NEW ③ — Cramér's V for categorical–categorical correlation
# ----------------------------------------------------------
def _cramers_v(x: pd.Series, y: pd.Series) -> float:
    """
    Compute Cramér's V (bias-corrected) between two categorical series.
    Returns a value in [0, 1]; returns 0.0 on any failure.
    """
    try:
        ct = pd.crosstab(x, y)
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            return 0.0
        chi2, _, _, _ = chi2_contingency(ct, correction=False)
        n = int(ct.values.sum())
        if n == 0:
            return 0.0
        phi2 = chi2 / n
        r, k = ct.shape
        # Bias-corrected
        phi2_corr = max(0.0, phi2 - ((k - 1) * (r - 1)) / max(n - 1, 1))
        r_corr = r - (r - 1) ** 2 / max(n - 1, 1)
        k_corr = k - (k - 1) ** 2 / max(n - 1, 1)
        denom = min(r_corr - 1, k_corr - 1)
        if denom <= 0:
            return 0.0
        return float(round(np.sqrt(phi2_corr / denom), 3))
    except Exception:
        return 0.0


def compute_categorical_correlation_signals(df, categorical_cols, threshold=0.7):
    """
    Returns pairs of categorical columns with Cramér's V >= threshold.
    Capped at 15 columns to keep runtime reasonable.
    """
    cols = categorical_cols[:15]
    pairs = []
    for i in range(len(cols)):
        for j in range(i):
            a, b = cols[i], cols[j]
            # Drop rows where either is null for the pair
            sub = df[[a, b]].dropna()
            if len(sub) < 10:
                continue
            v = _cramers_v(sub[a].astype(str), sub[b].astype(str))
            if v >= threshold:
                pairs.append({"col1": a, "col2": b, "cramers_v": v})
    pairs.sort(key=lambda x: x["cramers_v"], reverse=True)
    return pairs


def compute_feature_stability(missing_pct, skewness, outlier_percentage, numerical_cols):

    feature_stability = {}

    for col in numerical_cols:

        missing_penalty = min(missing_pct.get(col, 0) / 100, 1)
        skew_penalty = min(abs(skewness.get(col, 0)) / 3, 1)
        outlier_penalty = min(outlier_percentage.get(col, 0) / 20, 1)

        score = (
            0.4 * missing_penalty +
            0.3 * skew_penalty +
            0.3 * outlier_penalty
        )

        feature_stability[col] = round(float(score), 3)

    return feature_stability


# ==========================================================
# JSON CLEANER (FINAL SAFETY NET)
# ==========================================================

def clean_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0
        return obj
    else:
        return obj


# ==========================================================
# Main EDA Engine
# ==========================================================

def run_eda(df, target_col):

    id_cols = detect_id_columns(df)
    candidate_cols = [c for c in df.columns if c not in id_cols + [target_col]]

    # ① Detect and quarantine datetime columns before type split
    datetime_cols = detect_datetime_columns(df, candidate_cols)
    feature_cols = [c for c in candidate_cols if c not in datetime_cols]

    numerical_cols, categorical_cols = detect_column_types(df, feature_cols)

    # ② Detect pseudo-categorical within numerical columns
    pseudo_categorical_cols = detect_pseudo_categorical(df, numerical_cols, threshold=10)

    missing_pct, high_missing, moderate_missing = compute_missing_signals(df, feature_cols)

    cardinality, dominant_ratio, high_cardinality, encoding_risk = \
        compute_categorical_signals(df, categorical_cols)

    (
        skewness,
        kurtosis_vals,
        high_skew,
        outlier_percentage,
        variance,
        low_variance,
        zero_variance,        # ④ new
        scale_spread,
        scaling_needed
    ) = compute_numerical_signals(df, numerical_cols)

    high_corr_pairs, multicollinearity_score = \
        compute_correlation_signals(df, numerical_cols)

    # ③ Cramér's V for categorical pairs
    cat_corr_pairs = compute_categorical_correlation_signals(df, categorical_cols)

    feature_stability = compute_feature_stability(
        missing_pct, skewness, outlier_percentage, numerical_cols
    )

    n_rows = df.shape[0]
    n_features = len(feature_cols)

    num_ratio = round(len(numerical_cols) / max(1, n_features), 2)
    cat_ratio = round(len(categorical_cols) / max(1, n_features), 2)

    dataset_flags = {
        # ── all original flags unchanged ──
        "has_high_missing": len(high_missing) > 0,
        "has_high_skew": len(high_skew) > 0,
        "has_multicollinearity": multicollinearity_score > 0,
        "needs_scaling": scaling_needed,
        "has_outliers": any(v > 5 for v in outlier_percentage.values()),
        "encoding_risk": len(encoding_risk) > 0,
        # ── new flags ──
        "has_datetime_columns": len(datetime_cols) > 0,           # ①
        "has_pseudo_categorical": len(pseudo_categorical_cols) > 0,  # ②
        "has_categorical_correlation": len(cat_corr_pairs) > 0,   # ③
        "has_zero_variance": len(zero_variance) > 0,              # ④
    }

    eda_summary = {
        # ── all original keys unchanged ──
        "dataset_shape": df.shape,
        "n_rows": n_rows,
        "n_features": n_features,
        "target_column": target_col,
        "numerical_columns": numerical_cols,
        "categorical_columns": categorical_cols,
        "numerical_ratio": num_ratio,
        "categorical_ratio": cat_ratio,
        "missing_percentage": missing_pct,
        "high_missing_columns": high_missing,
        "moderate_missing_columns": moderate_missing,
        "categorical_cardinality": cardinality,
        "dominant_ratio": dominant_ratio,
        "high_cardinality_columns": high_cardinality,
        "encoding_risk_columns": encoding_risk,
        "skewness": skewness,
        "kurtosis": kurtosis_vals,
        "high_skew_columns": high_skew,
        "outlier_percentage": outlier_percentage,
        "variance": variance,
        "low_variance_columns": low_variance,
        "multicollinearity_pairs": high_corr_pairs,
        "multicollinearity_score": multicollinearity_score,
        "scale_spread": scale_spread,
        "feature_stability": feature_stability,
        "dataset_flags": dataset_flags,
        # ── new additive keys ──
        "datetime_cols": datetime_cols,                            # ①
        "pseudo_categorical_columns": pseudo_categorical_cols,     # ②
        "categorical_correlation_pairs": cat_corr_pairs,          # ③
        "zero_variance_columns": zero_variance,                    # ④
    }

    return clean_for_json(eda_summary)
