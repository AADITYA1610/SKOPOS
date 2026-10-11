# src/dataset_analyzer.py

import pandas as pd

def analyze_dataset(df):

    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    missing_summary = df.isnull().mean().to_dict()
    cardinality = {col: df[col].nunique() for col in df.columns}

    return {
        "n_rows": df.shape[0],
        "n_cols": df.shape[1],
        "columns": df.columns.tolist(),
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "missing_summary": missing_summary,
        "cardinality": cardinality
    }
