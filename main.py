from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import pandas as pd
import io

from src.auth_api import activity_router, auth_router, init_auth_db
from src.model_decision_engine import generate_model_decision_output
from src.eda_engine import run_eda
from src.preprocessing_planner import generate_preprocessing_plan
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
    return {"message": "Tadaa Backend Running 🚀"}


@app.post("/analyze-dataset")
async def analyze_dataset_endpoint(file: UploadFile = File(...)):

    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    result = generate_model_decision_output(df)

    return clean_for_json(result)


@app.post("/run-eda")
async def run_eda_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form("")
):

    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    eda_summary = run_eda(df, target_col)

    insights = generate_insights(eda_summary)
    quality = compute_dataset_quality(eda_summary)

    return clean_for_json({
    "eda_summary": eda_summary,
    "insights": insights,
    "dataset_quality": quality
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

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    try:
        overrides = json.loads(imputation_overrides or "{}")
        if not isinstance(overrides, dict):
            overrides = {}
    except json.JSONDecodeError:
        overrides = {}

    eda_summary = run_eda(df, target_col)

    plan = generate_preprocessing_plan(
        eda_summary=eda_summary,
        task_type=task_type,
        model_family=model_family,
        df=df,
        imputation_overrides=overrides,
    )

    return clean_for_json(plan)


@app.post("/recompute-decision")
async def recompute_decision(
    file: UploadFile = File(...),
    target_col: str = Form(...),
    task_type: str = Form("")
):

    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    if not target_col or target_col not in df.columns:
        return clean_for_json({
            "selected_target": None,
            "inferred_task": None,
            "model_family_recommendation": None,
            "confidence": None,
            "reasons": []
        })

    analysis = analyze_dataset(df)

    auto_inferred_task = infer_task_type(df, target_col)

    # Infer task if not provided
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

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    charts = generate_dashboard(df, target_col)

    return clean_for_json({"charts": charts})


@app.post("/dashboard-data")
async def dashboard_data_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form(""),
):
    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    if target_col and target_col not in df.columns:
        return {"error": "Invalid target column"}

    # Run EDA once — the payload builder reads pre-computed signals from it
    # instead of re-deriving correlations, missing %, variances, etc.
    eda_summary = run_eda(df, target_col)

    payload = build_dashboard_payload(df, target_col, eda_summary)
    return clean_for_json(payload)
@app.post("/custom-chart")
async def custom_chart_endpoint(
    file: UploadFile = File(...),
    chart_type: str = Form(...),
    x_col: str = Form(...),
    y_col: str = Form(""),
):
    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception:
        return {"error": "Invalid CSV file"}

    if x_col not in df.columns:
        return {"error": "Invalid X column"}

    if y_col and y_col not in df.columns:
        return {"error": "Invalid Y column"}

    from src.custom_chart_engine import generate_custom_chart

    panel = generate_custom_chart(df, chart_type, x_col, y_col)

    return clean_for_json(panel)