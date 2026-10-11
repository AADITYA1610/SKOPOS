import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import numpy as np
import pandas as pd

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")

    plt.close(fig)

    return img_base64


def generate_dashboard(df, target):

    charts = []

    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    numeric_cols = [c for c in numeric_cols if c != target]
    cat_cols = [c for c in cat_cols if c != target]

    # Chart 1 — Target distribution
    fig, ax = plt.subplots()

    if target in cat_cols:
        df[target].value_counts().plot(kind="bar", ax=ax)
    else:
        sns.histplot(df[target], kde=True, ax=ax)

    ax.set_title(f"{target} Distribution")

    charts.append(fig_to_base64(fig))

    # Chart 2 — Numeric distribution
    if numeric_cols:

        fig, ax = plt.subplots()

        sns.histplot(df[numeric_cols[0]], kde=True, ax=ax)

        ax.set_title(f"Distribution of {numeric_cols[0]}")

        charts.append(fig_to_base64(fig))

    # Chart 3 — Feature vs Target
    if target in cat_cols and numeric_cols:

        fig, ax = plt.subplots()

        sns.boxplot(x=df[target], y=df[numeric_cols[0]], ax=ax)

        ax.set_title(f"{numeric_cols[0]} vs {target}")

        charts.append(fig_to_base64(fig))

    # Chart 4 — Correlation Heatmap
    if len(numeric_cols) > 1:

        fig, ax = plt.subplots()

        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", ax=ax)

        ax.set_title("Feature Correlation")

        charts.append(fig_to_base64(fig))

    return charts