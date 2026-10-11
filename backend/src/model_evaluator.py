import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, r2_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import LabelEncoder


def get_model(task_type, model_family):
    if model_family == "neural_network":
        model_family = "tree_based"

    if task_type in ["binary_classification", "multiclass_classification"]:
        if model_family == "tree_based":
            return RandomForestClassifier(
                n_estimators=150,
                random_state=42,
                class_weight="balanced",
            )

        return LogisticRegression(
            max_iter=2000,
            random_state=42,
            class_weight="balanced",
        )

    if task_type == "regression":
        if model_family == "tree_based":
            return RandomForestRegressor(
                n_estimators=150,
                random_state=42,
            )

        return LinearRegression()

    return None


def prepare_for_model(df, target_col, task_type):
    df = df.copy()

    if target_col not in df.columns:
        return None, None

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    if len(df) < 10:
        return None, None

    X = df.drop(columns=[target_col])
    y = df[target_col]

    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    if task_type in ["binary_classification", "multiclass_classification"]:
        if not pd.api.types.is_numeric_dtype(y):
            le = LabelEncoder()
            y = le.fit_transform(y.astype(str))

        y = pd.Series(y)

    elif task_type == "regression":
        y = pd.to_numeric(y, errors="coerce")
        valid = ~pd.isna(y)
        X = X.loc[valid]
        y = y.loc[valid]

    return X, y


def _can_use_cv(y, task_type, min_splits=3):
    if task_type not in ["binary_classification", "multiclass_classification"]:
        return len(y) >= min_splits

    counts = pd.Series(y).value_counts()

    if len(counts) < 2:
        return False

    return counts.min() >= min_splits


def evaluate_model(df, target_col, task_type, model_family):
    X, y = prepare_for_model(df, target_col, task_type)

    if X is None or y is None or len(X) < 10:
        return None

    model = get_model(task_type, model_family)

    if model is None:
        return None

    try:
        if task_type in ["binary_classification", "multiclass_classification"]:
            metric = "accuracy"

            if _can_use_cv(y, task_type, min_splits=3):
                cv = StratifiedKFold(
                    n_splits=3,
                    shuffle=True,
                    random_state=42,
                )

                scores = cross_val_score(
                    model,
                    X,
                    y,
                    cv=cv,
                    scoring="accuracy",
                )

                return {
                    "metric": metric,
                    "score": round(float(scores.mean()), 4),
                    "cv_scores": [round(float(s), 4) for s in scores],
                    "evaluation_method": "3-fold stratified cross-validation",
                    "n_rows_used": int(len(X)),
                    "n_features_used": int(X.shape[1]),
                }

            stratify = y

            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42,
                    stratify=stratify,
                )
            except Exception:
                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42,
                )

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            score = accuracy_score(y_test, preds)

            return {
                "metric": metric,
                "score": round(float(score), 4),
                "evaluation_method": "single 80/20 train-test split",
                "n_rows_used": int(len(X)),
                "n_features_used": int(X.shape[1]),
            }

        if task_type == "regression":
            metric = "r2_score"

            if len(X) >= 15:
                cv = KFold(
                    n_splits=3,
                    shuffle=True,
                    random_state=42,
                )

                scores = cross_val_score(
                    model,
                    X,
                    y,
                    cv=cv,
                    scoring="r2",
                )

                return {
                    "metric": metric,
                    "score": round(float(scores.mean()), 4),
                    "cv_scores": [round(float(s), 4) for s in scores],
                    "evaluation_method": "3-fold cross-validation",
                    "n_rows_used": int(len(X)),
                    "n_features_used": int(X.shape[1]),
                }

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            score = r2_score(y_test, preds)

            return {
                "metric": metric,
                "score": round(float(score), 4),
                "evaluation_method": "single 80/20 train-test split",
                "n_rows_used": int(len(X)),
                "n_features_used": int(X.shape[1]),
            }

        return None

    except Exception as e:
        print("Model evaluation failed:", e)
        return None