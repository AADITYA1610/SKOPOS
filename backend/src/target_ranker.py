def score_target_column(df, col, analysis):
    score = 0
    reasons = []

    col_lower = col.lower()
    n_rows = analysis["n_rows"]

    unique_vals = df[col].nunique(dropna=False)
    unique_ratio = unique_vals / max(n_rows, 1)
    col_index = list(df.columns).index(col)

    # Strong target-like keywords
    strong_keywords = [
        "target", "label", "class", "outcome", "result", "status",
        "survived", "survival", "churn", "default", "fraud",
        "passed", "failed", "approved", "accepted", "diagnosis",
        "disease", "risk", "score", "price", "sales", "revenue"
    ]

    # Common feature/input columns that should usually NOT be targets
    feature_like_keywords = [
        "sex", "gender", "age", "name", "id", "uuid", "passengerid",
        "customerid", "employeeid", "email", "phone", "address",
        "city", "state", "country", "zipcode", "pclass", "ticket",
        "fare", "embarked", "cabin"
    ]

    # 1. Name-based target boost
    if any(keyword in col_lower for keyword in strong_keywords):
        score += 8
        reasons.append("Column name strongly suggests it is a prediction target")

    # 2. Penalize obvious input/identity/demographic fields
    if any(keyword == col_lower or keyword in col_lower for keyword in feature_like_keywords):
        score -= 6
        reasons.append("Column name looks like an input feature, not a prediction target")

    # 3. Binary target suitability
    if unique_vals == 2:
        score += 3
        reasons.append("Binary variable suitable for classification")

        value_counts = df[col].value_counts(normalize=True)

        if len(value_counts) > 1 and value_counts.min() > 0.2:
            score += 2
            reasons.append("Balanced distribution across classes")

    # 4. Low-cardinality categorical target suitability
    if col in analysis.get("categorical_cols", []) and 2 < unique_vals <= 15:
        score += 2
        reasons.append("Low-cardinality categorical variable")

    # 5. Regression-style numeric target suitability
    if col in analysis.get("numeric_cols", []) and 5 < unique_vals < 0.5 * n_rows:
        score += 2
        reasons.append("Numeric variable suitable for regression")

    # 6. Small position preference, but not too strong
    if col_index > 0.7 * len(df.columns):
        score += 1
        reasons.append("Column appears near the end of dataset")

    # 7. Penalize identifier-like columns
    if unique_ratio > 0.8:
        score -= 8
        reasons.append("High uniqueness — likely identifier, not target")

    # 8. Penalize columns with too many missing target values
    missing_ratio = df[col].isna().mean()

    if missing_ratio > 0.4:
        score -= 4
        reasons.append("High missingness makes this a weak target candidate")

    if not reasons:
        reasons.append("Column is a possible target but has weak target-like signals")

    return score, reasons


def rank_target_candidates(df, candidates, analysis):
    if not candidates:
        return []

    valid_candidates = []
    seen = set()

    for col in df.columns:
        if col in candidates and col not in seen:
            valid_candidates.append(col)
            seen.add(col)

    scored = []

    for col in valid_candidates:
        score, reasons = score_target_column(df, col, analysis)

        scored.append({
            "column": col,
            "score": score,
            "reasons": reasons,
            "unique_values": int(df[col].nunique(dropna=False)),
            "missing_values": int(df[col].isna().sum()),
            "column_index": int(list(df.columns).index(col)),
        })

    scored.sort(
        key=lambda x: (
            -x["score"],
            -x["column_index"],
            x["column"].lower(),
        )
    )

    return scored


def select_best_target(df, candidates, analysis):
    ranked = rank_target_candidates(df, candidates, analysis)

    if not ranked:
        return None

    return ranked[0]