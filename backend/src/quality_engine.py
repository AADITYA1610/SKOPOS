def compute_dataset_quality(eda_summary):

    score = 100
    breakdown = {}

    # Missing data penalty
    high_missing = len(eda_summary.get("high_missing_columns", []))
    moderate_missing = len(eda_summary.get("moderate_missing_columns", []))

    missing_penalty = high_missing * 8 + moderate_missing * 3
    score -= missing_penalty

    breakdown["missing_data_penalty"] = missing_penalty

    # Skew penalty
    skew_cols = len(eda_summary.get("high_skew_columns", []))
    skew_penalty = skew_cols * 2
    score -= skew_penalty

    breakdown["skew_penalty"] = skew_penalty

    # Outlier penalty
    outliers = eda_summary.get("dataset_flags", {}).get("has_outliers", False)
    outlier_penalty = 6 if outliers else 0
    score -= outlier_penalty

    breakdown["outlier_penalty"] = outlier_penalty

    # Multicollinearity penalty
    multi = eda_summary.get("multicollinearity_score", 0)
    multi_penalty = multi * 2
    score -= multi_penalty

    breakdown["multicollinearity_penalty"] = multi_penalty

    # Scaling penalty
    scaling = eda_summary.get("dataset_flags", {}).get("needs_scaling", False)
    scaling_penalty = 3 if scaling else 0
    score -= scaling_penalty

    breakdown["scaling_penalty"] = scaling_penalty

    if score < 0:
        score = 0

    return {
        "quality_score": score,
        "breakdown": breakdown
    }