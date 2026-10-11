from src.dataset_analyzer import analyze_dataset
from src.target_detector import detect_target_candidates
from src.task_inference import infer_task_type
from src.model_recommender import recommend_model_family
from src.target_ranker import select_best_target, score_target_column, rank_target_candidates


def generate_model_decision_output(df):
    analysis = analyze_dataset(df)

    raw_target_candidates = detect_target_candidates(df, analysis)

    # Make target candidates deterministic.
    # detect_target_candidates may return unordered / unstable candidates,
    # so we normalize them according to actual dataframe column order.
    target_candidates = [
        col for col in df.columns
        if col in raw_target_candidates
    ]

    ranked_target_candidates = rank_target_candidates(
        df=df,
        candidates=target_candidates,
        analysis=analysis,
    )

    best_target = select_best_target(
        df=df,
        candidates=target_candidates,
        analysis=analysis,
    )

    selected_target = None
    reasons = []
    confidence = None
    target_score = None

    if best_target:
        selected_target = best_target["column"]
        reasons = best_target["reasons"]
        score = best_target["score"]
        target_score = score

        if score >= 7:
            confidence = "Strong target candidate"
        elif score >= 4:
            confidence = "Moderate target candidate"
        else:
            confidence = "Weak target candidate"

    inferred_task = infer_task_type(df, selected_target)
    auto_inferred_task = inferred_task

    if selected_target:
        target_score, _ = score_target_column(df, selected_target, analysis)

    model_recommendation = recommend_model_family(inferred_task, analysis)

    output = {
        "dataset_summary": {
            **analysis,
            "n_features": analysis.get("n_cols", analysis.get("n_features")),
            "columns": list(df.columns),
        },

        # Backward-compatible: dropdown still receives simple column names
        "target_candidates": [item["column"] for item in ranked_target_candidates],

        # New: detailed ranked target info for debugging / UI later
        "target_candidate_details": ranked_target_candidates,

        "selected_target": selected_target,
        "target_confidence": confidence,
        "target_score": target_score,
        "target_reasons": reasons,

        "inferred_task": inferred_task,
        "auto_inferred_task": auto_inferred_task,
        "model_family_recommendation": model_recommendation,

        "preview_rows": df.head(10).to_dict(orient="records"),

        "column_summary": [
            {
                "column": col,
                "dtype": str(df[col].dtype),
                "missing": int(df[col].isna().sum()),
                "unique": int(df[col].nunique(dropna=False)),
            }
            for col in df.columns
        ],
    }

    return output