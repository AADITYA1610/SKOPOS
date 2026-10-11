def infer_task_type(df, target_col):

    if target_col is None:
        return "unsupervised"

    n_unique = df[target_col].nunique()
    total_rows = df.shape[0]
    dtype = df[target_col].dtype

    unique_ratio = n_unique / total_rows

    # Binary
    if n_unique == 2:
        return "binary_classification"

    # Multiclass
    if n_unique <= 15 and unique_ratio < 0.3:
        return "multiclass_classification"

    # Numeric regression
    if str(dtype).startswith(("int", "float")) and n_unique > 15:
        return "regression"

    return "needs_user_confirmation"