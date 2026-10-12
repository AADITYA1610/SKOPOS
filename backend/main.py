from src.stream_api import router as stream_router
from contextlib import asynccontextmanager
import os
import json
import io

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from src.auth_api import activity_router, auth_router, init_auth_db
from src.model_decision_engine import generate_model_decision_output
from src.eda_engine import run_eda
from src.preprocessing_planner import generate_preprocessing_plan
from src.preprocessing_executor import apply_preprocessing_plan
from src.model_evaluator import evaluate_model
from src.task_inference import infer_task_type
from src.model_recommender import recommend_model_family
from src.dataset_analyzer import analyze_dataset
from src.dashboard_generator import generate_dashboard
from src.dashboard_payload import build_dashboard_payload
from src.insight_generator import generate_insights
from src.quality_engine import compute_dataset_quality
from src.target_ranker import score_target_column
from src.json_cleaner import clean_for_json


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_auth_db()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(stream_router)

_cors = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:5173")
_cors_origins = [o.strip() for o in _cors.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(activity_router)


@app.get("/")
def root():
    return {"message": "Loom Backend Running 🚀"}


def _read_csv_from_upload(contents):
    try:
        return pd.read_csv(io.StringIO(contents.decode("utf-8"))), None
    except Exception:
        return None, {"error": "Invalid CSV file"}


def _parse_overrides(imputation_overrides):
    try:
        overrides = json.loads(imputation_overrides or "{}")
        if not isinstance(overrides, dict):
            return {}
        return overrides
    except json.JSONDecodeError:
        return {}


def _calculate_pipeline_change(before_eval, after_eval):
    before_score = before_eval.get("score") if before_eval else None
    after_score = after_eval.get("score") if after_eval else None

    improvement = None
    improvement_percentage = None
    performance_direction = None
    result_message = None

    if before_score is not None and after_score is not None:
        improvement = round(after_score - before_score, 4)

        if before_score != 0:
            improvement_percentage = round((improvement / abs(before_score)) * 100, 2)

        if improvement > 0:
            performance_direction = "improved"
            result_message = "The processed dataset performed better than the baseline."
        elif improvement < 0:
            performance_direction = "degraded"
            result_message = (
                "The processed dataset performed lower than the baseline. "
                "This can happen when preprocessing removes or changes useful signal for the selected model."
            )
        else:
            performance_direction = "unchanged"
            result_message = "The processed dataset produced the same score as the baseline."

    return {
        "before_score": before_score,
        "after_score": after_score,
        "improvement": improvement,
        "improvement_percentage": improvement_percentage,
        "performance_direction": performance_direction,
        "result_message": result_message,
    }


@app.post("/analyze-dataset")
async def analyze_dataset_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    result = generate_model_decision_output(df)
    return clean_for_json(result)


@app.post("/run-eda")
async def run_eda_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form("")
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    eda_summary = run_eda(df, target_col)
    insights = generate_insights(eda_summary)
    quality = compute_dataset_quality(eda_summary)

    return clean_for_json({
        "eda_summary": eda_summary,
        "insights": insights,
        "dataset_quality": quality,
    })


@app.post("/generate-preprocessing-plan")
async def generate_preprocessing_plan_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form(""),
    task_type: str = Form(""),
    model_family: str = Form(""),
    imputation_overrides: str = Form("{}"),
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    overrides = _parse_overrides(imputation_overrides)

    eda_summary = run_eda(df, target_col)

    plan = generate_preprocessing_plan(
        eda_summary=eda_summary,
        task_type=task_type,
        model_family=model_family,
        df=df,
        imputation_overrides=overrides,
    )

    return clean_for_json(plan)


@app.post("/execute-pipeline")
async def execute_pipeline_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form(...),
    task_type: str = Form(...),
    model_family: str = Form(...),
    imputation_overrides: str = Form("{}"),
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if not target_col or target_col not in df.columns:
        return {"error": "Invalid target column"}

    overrides = _parse_overrides(imputation_overrides)

    eda_summary = run_eda(df, target_col)

    plan = generate_preprocessing_plan(
        eda_summary=eda_summary,
        task_type=task_type,
        model_family=model_family,
        df=df,
        imputation_overrides=overrides,
    )

    before_eval = evaluate_model(
        df=df,
        target_col=target_col,
        task_type=task_type,
        model_family=model_family,
    )

    processed_df = apply_preprocessing_plan(
        df=df,
        plan=plan,
        target_col=target_col,
    )

    after_eval = evaluate_model(
        df=processed_df,
        target_col=target_col,
        task_type=task_type,
        model_family=model_family,
    )

    metric = None
    if after_eval:
        metric = after_eval.get("metric")
    elif before_eval:
        metric = before_eval.get("metric")

    change = _calculate_pipeline_change(before_eval, after_eval)

    preview = processed_df.head(10).to_dict(orient="records")
    csv_data = processed_df.to_csv(index=False)

    return clean_for_json({
        "preprocessing_plan": plan,
        "metric": metric,
        "before_score": change["before_score"],
        "after_score": change["after_score"],
        "before_evaluation": before_eval,
        "after_evaluation": after_eval,
        "improvement": change["improvement"],
        "improvement_percentage": change["improvement_percentage"],
        "performance_direction": change["performance_direction"],
        "result_message": change["result_message"],
        "preview": preview,
        "columns": list(processed_df.columns),
        "shape": {
            "rows": int(processed_df.shape[0]),
            "columns": int(processed_df.shape[1]),
        },
        "original_shape": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
        },
        "csv": csv_data,
    })


@app.post("/recompute-decision")
async def recompute_decision(
    file: UploadFile = File(...),
    target_col: str = Form(...),
    task_type: str = Form("")
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if not target_col or target_col not in df.columns:
        return clean_for_json({
            "selected_target": None,
            "inferred_task": None,
            "model_family_recommendation": None,
            "confidence": None,
            "reasons": [],
        })

    analysis = analyze_dataset(df)
    auto_inferred_task = infer_task_type(df, target_col)

    if not task_type:
        task_type = auto_inferred_task

    model_recommendation = recommend_model_family(task_type, analysis)

    score, reasons = score_target_column(df, target_col, analysis)

    if score >= 7:
        confidence = "Strong target candidate"
    elif score >= 4:
        confidence = "Moderate target candidate"
    else:
        confidence = "Weak target candidate"

    return clean_for_json({
        "selected_target": target_col,
        "inferred_task": task_type,
        "auto_inferred_task": auto_inferred_task,
        "target_score": score,
        "model_family_recommendation": model_recommendation,
        "confidence": confidence,
        "target_confidence": confidence,
        "reasons": reasons,
        "target_reasons": reasons,
    })


@app.post("/generate-dashboard")
async def generate_dashboard_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form("")
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    charts = generate_dashboard(df, target_col)

    return clean_for_json({"charts": charts})


@app.post("/dashboard-data")
async def dashboard_data_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form(""),
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    payload = build_dashboard_payload(df, target_col)

    if "meta" not in payload or payload["meta"] is None:
        payload["meta"] = {}

    payload["meta"]["columns"] = list(df.columns)

    return clean_for_json(payload)


@app.post("/custom-chart")
async def custom_chart_endpoint(
    file: UploadFile = File(...),
    chart_type: str = Form(...),
    x_col: str = Form(""),
    y_col: str = Form(""),
    group_col: str = Form(""),
    aggregation: str = Form("none"),
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    if chart_type != "correlation" and x_col not in df.columns:
        return {"error": "Invalid X column"}

    if y_col and y_col not in df.columns:
        return {"error": "Invalid Y column"}

    if group_col and group_col not in df.columns:
        return {"error": "Invalid grouping column"}

    from src.custom_chart_engine import generate_custom_chart

    panel = generate_custom_chart(
        df=df,
        chart_type=chart_type,
        x=x_col,
        y=y_col,
        group_col=group_col,
        aggregation=aggregation,
    )

    if not panel.get("data"):
        return {"error": "Not enough valid data to generate this chart"}

    return clean_for_json(panel)


@app.post("/chat-viz")
async def chat_viz_endpoint(
    file: UploadFile = File(...),
    query: str = Form(...),
):
    contents = await file.read()
    df, error = _read_csv_from_upload(contents)

    if error:
        return error

    columns = df.columns.tolist()

    try:
        from src.klaus_engine import get_Klaus_response
        action = get_Klaus_response(query, columns)
    except Exception as e:
        return {"error": f"Klaus engine error: {str(e)}"}

    if not action:
        return {"error": "Klaus couldn't interpret that. Try: 'Compare total sales by region'."}

    cat_col = action.get("category", "")
    val_col = action.get("value", "")
    agg = action.get("aggregation", "sum").lower()
    chart_type = action.get("chart_type", "bar")

    if agg not in ["sum", "avg", "count"]:
        agg = "sum"

    if not cat_col or cat_col not in df.columns:
        return {"error": f"Column '{cat_col}' not found. Available: {', '.join(columns[:10])}"}

    if agg != "count" and (not val_col or val_col not in df.columns):
        return {"error": f"Column '{val_col}' not found. Available: {', '.join(columns[:10])}"}

    try:
        if chart_type == "scatter":
            if not val_col or val_col not in df.columns:
                return {"error": f"Column '{val_col}' not found. Available: {', '.join(columns[:10])}"}

            scatter_df = df[[cat_col, val_col]].copy()
            scatter_df[cat_col] = pd.to_numeric(scatter_df[cat_col], errors="coerce")
            scatter_df[val_col] = pd.to_numeric(scatter_df[val_col], errors="coerce")
            scatter_df = scatter_df.dropna().head(200)

            chart_data = [
                {"x": round(float(row[cat_col]), 4), "y": round(float(row[val_col]), 4)}
                for _, row in scatter_df.iterrows()
            ]

        else:
            if agg == "count":
                grouped = df.groupby(cat_col).size()
            else:
                temp = df[[cat_col]].copy()
                temp["_val"] = pd.to_numeric(df[val_col], errors="coerce")

                if agg == "avg":
                    grouped = temp.groupby(cat_col)["_val"].mean()
                else:
                    grouped = temp.groupby(cat_col)["_val"].sum()

            chart_data = [
                {"name": str(k)[:40], "value": round(float(v), 4)}
                for k, v in grouped.items()
                if pd.notna(v)
            ]

            chart_data.sort(key=lambda x: x["value"], reverse=True)
            chart_data = chart_data[:20]

    except Exception as exc:
        return {"error": f"Aggregation failed: {str(exc)}"}

    insight = ""

    if chart_data and chart_type != "scatter":
        top = chart_data[0]
        bottom = chart_data[-1]
        agg_label = {"sum": "total", "avg": "average", "count": "count"}.get(agg, agg)
        total_val = sum(x["value"] for x in chart_data)
        share_pct = round(top["value"] / total_val * 100, 1) if total_val else 0

        insight = (
            f"**{top['name']}** leads with the highest {agg_label} "
            f"({top['value']:,.2f}, {share_pct}% of total). "
            f"**{bottom['name']}** is lowest at {bottom['value']:,.2f}."
        )

    elif chart_data and chart_type == "scatter":
        insight = (
            f"This scatter plot compares **{cat_col}** against **{val_col}** "
            f"using {len(chart_data)} valid numeric points."
        )

    return clean_for_json({
        "action": action,
        "chart_data": chart_data,
        "insight": insight,
        "meta": {
            "category_col": cat_col,
            "value_col": val_col,
            "aggregation": agg,
            "chart_type": chart_type,
            "n_categories": len(chart_data),
        },
    })