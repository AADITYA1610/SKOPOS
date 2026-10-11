def _allowed_numeric_imputation(n_rows, pct):
    base = ["median", "mean", "constant"]
    if n_rows < 12000 and 0 < pct < 45:
        return ["median", "mean", "knn", "constant"]
    return base


def _allowed_categorical_imputation():
    return ["most_frequent", "constant"]


def recommend_imputation_entry(col, pct, eda_summary, df, drop_columns):
    if col in drop_columns:
        return None

    numerical_cols = eda_summary.get("numerical_columns") or []
    categorical_cols = eda_summary.get("categorical_columns") or []
    skew_map = eda_summary.get("skewness") or {}
    out_map = eda_summary.get("outlier_percentage") or {}
    dom_map = eda_summary.get("dominant_ratio") or {}
    n_rows = eda_summary.get("n_rows") or len(df)

    if col in numerical_cols:
        sk = abs(float(skew_map.get(col) or 0))
        op = float(out_map.get(col) or 0)
        alternatives = _allowed_numeric_imputation(n_rows, pct)
        parts = [f"{pct}% missing"]

        if sk > 1.0:
            method = "median"
            parts.append(f"strong skew (|skew|≈{sk:.2f}) — median is more robust than mean")
        elif op > 12:
            method = "median"
            parts.append(f"~{op}% values beyond IQR — median resists outlier pull")
        elif pct > 35:
            method = "median"
            parts.append("heavy missingness — median limits distortion from long tails")
        elif sk > 0.5:
            method = "median"
            parts.append("mild skew — median preferred for stability")
        else:
            method = "mean"
            parts.append("near-symmetric distribution — mean preserves expected value")

        return {
            "method": method,
            "recommended_method": method,
            "reason": "; ".join(parts),
            "alternatives": alternatives,
        }

    if col in categorical_cols:
        alternatives = _allowed_categorical_imputation()
        dom = dom_map.get(col)
        method = "most_frequent"
        parts = [f"{pct}% missing"]

        if dom is not None and float(dom) > 88:
            parts.append("one dominant category — mode imputation is usually safe")
        else:
            parts.append("categorical column — fill with most frequent observed value")

        return {
            "method": method,
            "recommended_method": method,
            "reason": "; ".join(parts),
            "alternatives": alternatives,
        }

    return {
        "method": "most_frequent",
        "recommended_method": "most_frequent",
        "reason": f"{pct}% missing; treating as categorical by default",
        "alternatives": _allowed_categorical_imputation(),
    }


def _apply_imputation_override(entry, col, imputation_overrides):
    if not imputation_overrides or col not in imputation_overrides:
        entry["user_override"] = False
        return entry

    chosen = str(imputation_overrides[col]).strip().lower().replace(" ", "_")
    rec = entry["recommended_method"]
    alts = [str(a).lower() for a in entry.get("alternatives", [])]

    if chosen == rec.lower() or chosen in alts:
        entry["method"] = chosen
        entry["user_override"] = chosen != rec.lower()
        if entry["user_override"]:
            entry["override_note"] = f"Using “{chosen}” instead of recommended “{rec}”."
    else:
        entry["user_override"] = False
        entry["override_note"] = f"Ignored unknown override “{chosen}”; kept recommended “{rec}”."

    return entry


def generate_preprocessing_plan(
    eda_summary,
    task_type,
    model_family,
    df,
    imputation_overrides=None
):
    imputation_overrides = imputation_overrides or {}

    preprocessing_plan = {
        "drop_columns": {},
        "imputation": {},
        "encoding": {},
        "transformation": {},
        "scaling": None,
        "feature_selection": None,
        "imbalance_handling": None,
        "dimensionality_reduction": None,
        "outlier_handling": None,
    }

    n_rows = eda_summary.get("n_rows") or len(df)
    n_features = eda_summary.get("n_features") or len(df.columns)

    numerical_cols = eda_summary.get("numerical_columns", [])
    high_skew_cols = eda_summary.get("high_skew_columns", [])
    skewness = eda_summary.get("skewness", {})
    missing_pct_map = eda_summary.get("missing_percentage", {})
    low_variance_cols = eda_summary.get("low_variance_columns", [])
    zero_variance_cols = eda_summary.get("zero_variance_columns", [])

    # =====================================================
    # DROP STRATEGY
    # =====================================================

    for col in df.columns:
        if df[col].nunique(dropna=True) == n_rows:
            preprocessing_plan["drop_columns"][col] = {
                "reason": "Column has unique value per row (ID-like feature)"
            }

        elif any(k in col.lower() for k in ["id", "uuid", "name"]):
            preprocessing_plan["drop_columns"][col] = {
                "reason": "Column name suggests identifier or non-generalizable feature"
            }

    for col, pct in missing_pct_map.items():
        if pct > 60:
            preprocessing_plan["drop_columns"][col] = {
                "reason": f"High missing percentage ({pct}%) > 60%"
            }

    for col in low_variance_cols:
        preprocessing_plan["drop_columns"][col] = {
            "reason": "Low variance feature — minimal predictive value"
        }

    for col in zero_variance_cols:
        preprocessing_plan["drop_columns"][col] = {
            "reason": "Zero variance feature — contains no predictive information"
        }

    # =====================================================
    # IMPUTATION
    # =====================================================

    for col, pct in missing_pct_map.items():
        if col in preprocessing_plan["drop_columns"]:
            continue

        if pct > 0:
            entry = recommend_imputation_entry(
                col,
                float(pct),
                eda_summary,
                df,
                preprocessing_plan["drop_columns"],
            )

            if entry:
                preprocessing_plan["imputation"][col] = _apply_imputation_override(
                    entry,
                    col,
                    imputation_overrides,
                )

    # =====================================================
    # ENCODING
    # =====================================================

    for col, card in eda_summary.get("categorical_cardinality", {}).items():
        if col in preprocessing_plan["drop_columns"]:
            continue

        if card <= 10:
            if model_family == "tree_based":
                method = "label"
                reason = "Tree-based models handle label encoding safely for low-cardinality categorical features"
            else:
                method = "onehot"
                reason = "Low-cardinality categorical feature — one-hot encoding avoids artificial ordering"

        elif card <= 50:
            if task_type != "unsupervised":
                method = "target"
                reason = "Medium-cardinality categorical feature — target encoding controls dimensionality"
            else:
                method = "frequency"
                reason = "Unsupervised task — target encoding is not allowed"

        else:
            if task_type != "unsupervised":
                method = "target"
                reason = "High-cardinality categorical feature — target encoding avoids excessive dummy columns"
            else:
                preprocessing_plan["drop_columns"][col] = {
                    "reason": "High-cardinality categorical feature unsuitable for unsupervised learning"
                }
                continue

        preprocessing_plan["encoding"][col] = {
            "method": method,
            "reason": reason,
        }

    # =====================================================
    # TRANSFORMATIONS / SKEWNESS CORRECTION
    # =====================================================

    for col in high_skew_cols:
        if col in preprocessing_plan["drop_columns"]:
            continue

        if col not in numerical_cols:
            continue

        skew_value = skewness.get(col, None)

        preprocessing_plan["transformation"][col] = {
            "method": "yeo_johnson_transform",
            "reason": f"High skewness detected (skew={skew_value}). Yeo-Johnson is safer than log because it supports zero and negative values.",
        }

    # =====================================================
    # SCALING
    # =====================================================

    if model_family in ["linear_model", "distance_based", "neural_network"]:
        method = "standard_scaler"
        reason = "Selected model family is scale-sensitive"

        if eda_summary.get("dataset_flags", {}).get("has_outliers"):
            method = "robust_scaler"
            reason = "Outliers detected — robust scaling reduces the influence of extreme values"

        preprocessing_plan["scaling"] = {
            "method": method,
            "reason": reason,
        }

    # =====================================================
    # IMBALANCE HANDLING
    # =====================================================

    if task_type in ["binary_classification", "multiclass_classification"]:
        imbalance_ratio = eda_summary.get("class_imbalance_ratio", 0)

        if imbalance_ratio > 0.4:
            if model_family == "tree_based":
                method = "class_weight"
                reason = f"Class imbalance ratio {imbalance_ratio} detected"
            else:
                method = "smote"
                reason = f"Class imbalance ratio {imbalance_ratio} detected"

            preprocessing_plan["imbalance_handling"] = {
                "method": method,
                "reason": reason,
            }

    # =====================================================
    # FEATURE SELECTION
    # =====================================================

    if eda_summary.get("multicollinearity_score", 0) > 0:
        preprocessing_plan["feature_selection"] = {
            "method": "remove_correlated_features",
            "reason": "High multicollinearity detected",
        }

    # =====================================================
    # DIMENSIONALITY REDUCTION
    # =====================================================

    if n_features > 100:
        preprocessing_plan["dimensionality_reduction"] = {
            "method": "pca",
            "reason": "High feature dimensionality",
        }

    # =====================================================
    # OUTLIER HANDLING
    # =====================================================

    if eda_summary.get("dataset_flags", {}).get("has_outliers"):
        preprocessing_plan["outlier_handling"] = {
            "method": "iqr_capping",
            "reason": "Outliers detected in numerical features",
        }

    return preprocessing_plan