def detect_target_candidates(df, analysis):

    candidates = []
    n_rows = analysis["n_rows"]

    for col in df.columns:

        unique_vals = df[col].nunique(dropna=False)
        unique_ratio = unique_vals / n_rows
        col_lower = col.lower()

        # ----------------------------
        # 🚫 HARD EXCLUSIONS
        # ----------------------------

        # ID-like columns
        if col_lower.endswith("_id") or col_lower == "id":
            continue

        if any(keyword in col_lower for keyword in ["uuid", "timestamp", "date", "time"]):
            continue
        if col in analysis.get("datetime_cols", []):
            continue
        # Too unique (almost every row different)
        if unique_ratio > 0.9:
            continue

        # Constant column
        if unique_vals <= 1:
            continue

        # Date columns
        if col in analysis.get("datetime_cols", []):
            continue

        # ----------------------------
        # 🎯 CANDIDATE RULES
        # ----------------------------

        # Strong name hint
        if any(keyword in col_lower for keyword in 
               ["target", "label", "class", "outcome", "result", "status"]):
            candidates.append(col)
            continue
        if col in analysis["numeric_cols"] and 5 < unique_vals < 0.5 * n_rows:
            candidates.append(col)

        # Binary columns
        if unique_vals == 2:
            candidates.append(col)
            continue

        # Low unique categorical (classification case)
        if col in analysis["categorical_cols"] and 2 < unique_vals <= 15:
            candidates.append(col)
            continue

        # Numeric but not too unique (possible regression)
        if col in analysis["numeric_cols"] and 5 < unique_vals < 0.5 * n_rows:
            candidates.append(col)

    return list(set(candidates))