import pandas as pd
import numpy as np


def generate_custom_chart(df, chart_type, x="", y="", group_col="", aggregation="none"):
    chart_map = {
        "box": "boxplot",
    }

    panel_chart_type = chart_map.get(chart_type, chart_type)

    panel = {
        "id": "custom",
        "title": f"{chart_type.upper()} ({x}{' vs ' + y if y else ''})",
        "subtitle": "User-generated custom visualization",
        "chart": panel_chart_type,
        "data": [],
    }

    # CORRELATION HEATMAP
    if chart_type == "correlation":
        # Convert possible numeric-looking strings into real numeric values
        numeric_df = df.apply(pd.to_numeric, errors="coerce")

        # Remove columns that are completely empty after conversion
        numeric_df = numeric_df.dropna(axis=1, how="all")

        # Remove constant columns because correlation becomes NaN
        numeric_df = numeric_df.loc[:, numeric_df.nunique(dropna=True) > 1]

        if numeric_df.shape[1] < 2:
            return panel

        # Limit columns to avoid huge unreadable heatmap
        numeric_df = numeric_df.iloc[:, :20]

        corr = numeric_df.corr(method="pearson").fillna(0).round(3)

        panel["id"] = "custom_correlation"
        panel["title"] = "Correlation Heatmap"
        panel["subtitle"] = "Pearson correlation between numeric features"
        panel["chart"] = "heatmap"
        panel["labels"] = list(corr.columns)
        panel["matrix"] = corr.astype(float).values.tolist()

        # Required so backend validation does not reject empty data.
        panel["data"] = [{"name": "correlation", "value": 1}]

    elif chart_type == "bar":
        if aggregation == "count" or aggregation == "none" or not y:
            counts = df[x].astype(str).value_counts().head(30)
            panel["data"] = [
                {"name": str(k), "value": int(v)}
                for k, v in counts.items()
            ]
        else:
            temp = df[[x, y]].copy()
            temp[y] = pd.to_numeric(temp[y], errors="coerce")
            temp = temp.dropna()

            if aggregation == "sum":
                grouped = temp.groupby(x)[y].sum().head(30)
            elif aggregation == "avg":
                grouped = temp.groupby(x)[y].mean().head(30)
            else:
                grouped = temp.groupby(x)[y].count().head(30)

            panel["data"] = [
                {"name": str(k), "value": float(v)}
                for k, v in grouped.items()
            ]

    elif chart_type == "histogram":
        s = pd.to_numeric(df[x], errors="coerce").dropna()

        if len(s) > 0:
            counts, bins = np.histogram(s, bins=15)

            panel["data"] = [
                {
                    "label": f"{bins[i]:.2f}-{bins[i + 1]:.2f}",
                    "value": int(counts[i]),
                }
                for i in range(len(counts))
                if counts[i] > 0
            ]

    elif chart_type == "scatter" and y:
        sub = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()

        if len(sub) > 0:
            sub = sub.sample(min(len(sub), 500), random_state=42)

            panel["data"] = [
                {"x": float(r[x]), "y": float(r[y])}
                for _, r in sub.iterrows()
            ]

    elif chart_type == "line" and y:
        temp = df[[x, y]].copy()
        temp[y] = pd.to_numeric(temp[y], errors="coerce")
        temp = temp.dropna()

        if aggregation in ["sum", "avg", "count"]:
            if aggregation == "sum":
                grouped = temp.groupby(x)[y].sum().reset_index()
            elif aggregation == "avg":
                grouped = temp.groupby(x)[y].mean().reset_index()
            else:
                grouped = temp.groupby(x)[y].count().reset_index()

            panel["data"] = [
                {"name": str(row[x]), "value": float(row[y])}
                for _, row in grouped.head(50).iterrows()
            ]
        else:
            panel["data"] = [
                {"name": str(row[x]), "value": float(row[y])}
                for _, row in temp.head(100).iterrows()
            ]

    elif chart_type == "box" and y:
        grouped = df.groupby(x)[y]

        boxes = []

        for cat, values in grouped:
            vals = pd.to_numeric(values, errors="coerce").dropna()

            if len(vals) < 5:
                continue

            boxes.append({
                "category": str(cat),
                "min": float(vals.min()),
                "q1": float(vals.quantile(0.25)),
                "median": float(vals.median()),
                "q3": float(vals.quantile(0.75)),
                "max": float(vals.max()),
                "n": int(len(vals)),
            })

        panel["data"] = boxes[:30]

    return panel