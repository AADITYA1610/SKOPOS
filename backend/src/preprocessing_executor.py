import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler, RobustScaler, LabelEncoder, PowerTransformer
from sklearn.impute import KNNImputer


def _safe_numeric_series(series):
    return pd.to_numeric(series, errors="coerce")


def _encode_target_for_mean(y):
    if pd.api.types.is_numeric_dtype(y):
        return y

    le = LabelEncoder()
    return pd.Series(le.fit_transform(y.astype(str)), index=y.index)


def apply_preprocessing_plan(df, plan, target_col=None):
    df = df.copy()

    # =====================================================
    # DROP
    # =====================================================

    drop_cols = list(plan.get("drop_columns", {}).keys())
    drop_cols = [c for c in drop_cols if c in df.columns and c != target_col]
    df = df.drop(columns=drop_cols, errors="ignore")

    # =====================================================
    # IMPUTATION
    # =====================================================

    for col, info in plan.get("imputation", {}).items():
        if col not in df.columns or col == target_col:
            continue

        method = info.get("method")

        if method in ["mean", "median", "knn"]:
            df[col] = _safe_numeric_series(df[col])

        if method == "mean":
            df[col] = df[col].fillna(df[col].mean())

        elif method == "median":
            df[col] = df[col].fillna(df[col].median())

        elif method == "most_frequent":
            mode = df[col].mode(dropna=True)
            df[col] = df[col].fillna(mode.iloc[0] if len(mode) else "Unknown")

        elif method == "constant":
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("Unknown")

        elif method == "knn":
            imputer = KNNImputer(n_neighbors=5)
            df[[col]] = imputer.fit_transform(df[[col]])

    # =====================================================
    # ENCODING
    # =====================================================

    for col, info in plan.get("encoding", {}).items():
        if col not in df.columns or col == target_col:
            continue

        method = info.get("method")

        if method == "label":
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))

        elif method == "onehot":
            dummies = pd.get_dummies(df[col].astype(str), prefix=col, drop_first=True)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)

        elif method == "frequency":
            freq = df[col].astype(str).value_counts(normalize=True)
            df[col] = df[col].astype(str).map(freq).fillna(0)

        elif method == "target" and target_col and target_col in df.columns:
            encoded_target = _encode_target_for_mean(df[target_col])

            temp = pd.DataFrame({
                col: df[col].astype(str),
                "__target_encoded__": encoded_target,
            })

            target_mean = temp.groupby(col)["__target_encoded__"].mean()
            global_mean = encoded_target.mean()

            df[col] = df[col].astype(str).map(target_mean).fillna(global_mean)

    # =====================================================
    # TRANSFORMATIONS / SKEWNESS CORRECTION
    # =====================================================

    for col, info in plan.get("transformation", {}).items():
        if col not in df.columns or col == target_col:
            continue

        method = info.get("method")

        numeric = _safe_numeric_series(df[col]).fillna(0)

        if method == "log_transform":
            min_val = numeric.min()

            if pd.notna(min_val) and min_val < 0:
                numeric = numeric - min_val

            df[col] = np.log1p(numeric)

        elif method == "yeo_johnson_transform":
            try:
                transformer = PowerTransformer(method="yeo-johnson", standardize=False)
                df[[col]] = transformer.fit_transform(numeric.values.reshape(-1, 1))
            except Exception:
                min_val = numeric.min()

                if pd.notna(min_val) and min_val < 0:
                    numeric = numeric - min_val

                df[col] = np.log1p(numeric)

    # =====================================================
    # OUTLIER CAPPING
    # =====================================================

    if plan.get("outlier_handling"):
        for col in df.select_dtypes(include=np.number).columns:
            if col == target_col:
                continue

            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1

            if pd.isna(iqr) or iqr == 0:
                continue

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            df[col] = np.clip(df[col], lower, upper)

    # =====================================================
    # FEATURE SELECTION
    # =====================================================

    if plan.get("feature_selection"):
        numeric_df = df.select_dtypes(include=np.number)

        if numeric_df.shape[1] > 1:
            corr_matrix = numeric_df.corr().abs()
            upper = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )

            to_drop = [
                col for col in upper.columns
                if col != target_col and any(upper[col] > 0.9)
            ]

            df = df.drop(columns=to_drop, errors="ignore")

    # =====================================================
    # SCALING
    # =====================================================

    scaling_info = plan.get("scaling")

    if scaling_info:
        method = scaling_info.get("method")

        if method == "standard_scaler":
            scaler = StandardScaler()
        elif method == "robust_scaler":
            scaler = RobustScaler()
        else:
            scaler = None

        if scaler:
            num_cols = df.select_dtypes(include=np.number).columns.tolist()

            if target_col in num_cols:
                num_cols.remove(target_col)

            if num_cols:
                df[num_cols] = scaler.fit_transform(df[num_cols])

    return df