# src/pipelines.py

import json
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    OneHotEncoder, PowerTransformer
)
from sklearn.impute import SimpleImputer


def build_pipelines(X, preprocessing_plan):
    numerical_cols = X.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=np.number).columns.tolist()

    num_imputer = SimpleImputer(strategy="median")
    cat_imputer = SimpleImputer(strategy="most_frequent")

    cat_encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False
    )

    power = PowerTransformer() if preprocessing_plan["transformation"] else "passthrough"

    scalers = {
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
        "robust": RobustScaler()
    }

    pipelines = {}

    for name, scaler in scalers.items():
        num_pipeline = Pipeline([
            ("imputer", num_imputer),
            ("power", power),
            ("scaler", scaler)
        ])

        cat_pipeline = Pipeline([
            ("imputer", cat_imputer),
            ("encoder", cat_encoder)
        ])

        preprocessor = ColumnTransformer([
            ("num", num_pipeline, numerical_cols),
            ("cat", cat_pipeline, categorical_cols)
        ])

        pipelines[name] = Pipeline([
            ("preprocessor", preprocessor)
        ])

    return pipelines
