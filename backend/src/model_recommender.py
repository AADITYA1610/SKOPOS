# src/model_recommender.py

def recommend_model_family(task_type, analysis):

    n_rows = analysis["n_rows"]
    n_cols = analysis["n_cols"]

    recommendation = {}
    reasons = []

    if task_type in ["binary_classification", "multiclass_classification"]:

        if n_rows < 5000 and n_cols < 50:
            recommendation["primary"] = "tree_based"
            recommendation["secondary"] = "linear_model"

            reasons.append("Small to medium dataset size")
            reasons.append("Tree models handle mixed feature types well")
            reasons.append("Linear models provide interpretable baseline")

        elif n_cols > 100:
            recommendation["primary"] = "linear_model"
            recommendation["secondary"] = "tree_based"

            reasons.append("High feature count favors linear models")
            reasons.append("Tree models used as secondary non-linear alternative")

        else:
            recommendation["primary"] = "tree_based"
            recommendation["secondary"] = "neural_network"

            reasons.append("Moderate feature space")
            reasons.append("Tree models capture non-linear patterns well")
            reasons.append("Neural networks as secondary deep pattern learner")

    elif task_type == "regression":

        if n_cols < 30:
            recommendation["primary"] = "linear_model"
            recommendation["secondary"] = "tree_based"

            reasons.append("Low feature count suits linear regression")
            reasons.append("Tree models capture non-linear relationships")

        else:
            recommendation["primary"] = "tree_based"
            recommendation["secondary"] = "neural_network"

            reasons.append("Higher dimensional feature space")
            reasons.append("Tree models robust to complex relationships")

    else:
        recommendation["primary"] = "exploration_required"
        reasons.append("Task type unclear — manual exploration recommended")

    recommendation["reasons"] = reasons

    return recommendation