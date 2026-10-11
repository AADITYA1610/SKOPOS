import streamlit as st
import pandas as pd
import numpy as np
MAX_FILE_SIZE_MB=200

from src.model_decision_engine import generate_model_decision_output
from src.task_inference import infer_task_type
from src.model_recommender import recommend_model_family
from src.eda_engine import run_eda, run_eda

st.set_page_config(
    page_title="TADA - Data to Decisions",
    layout="wide"
)
# -----------------------------------
# Title
# -----------------------------------
st.title("🚀 TADA")
st.subheader("Data → Decisions. Instantly.")
st.markdown("---")
# -----------------------------------
# File Upload
# -----------------------------------
uploaded_file = st.file_uploader(
    f"Upload your dataset (CSV or Excel only, Max {MAX_FILE_SIZE_MB}MB)",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file is not None:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    df = pd.read_csv(uploaded_file)

    if file_size_mb > MAX_FILE_SIZE_MB:
        st.error(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
        st.stop()
    else:
        st.success("File uploaded successfully!")

    # -----------------------------------
    # Dataset Overview
    # -----------------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Rows", df.shape[0])
    col2.metric("Columns", df.shape[1])
    col3.metric("Missing Values", int(df.isnull().sum().sum()))

    st.markdown("---")

    # -----------------------------------
    # Data Preview
    # -----------------------------------
    st.subheader("🔍 Data Preview")
    st.dataframe(df.head(),hide_index=True)

    st.markdown("---")

    # -----------------------------------
    # Column Summary
    # -----------------------------------
    st.subheader("📊 Column Summary")

    summary_df = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": df.dtypes.astype(str),
        "Missing Values": df.isnull().sum(),
        "Unique Values": df.nunique()
    })

    st.dataframe(summary_df,use_container_width=True, hide_index=True)

    st.markdown("---")

    # ===================================
    # MODEL DECISION SECTION
    # ===================================

    st.header("🧠 Model Direction Engine")

    result = generate_model_decision_output(df)

    detected_target_candidates = result["target_candidates"]
    auto_target = result["selected_target"]
    auto_task = result["inferred_task"]
    auto_model_family = result["model_family_recommendation"]

    # -----------------------------------
    # Target Selection
    # -----------------------------------
    st.subheader("🎯 Select Target Variable")

    if len(detected_target_candidates) > 0:
        selected_target = st.selectbox(
            "We detected possible target columns:",
            options=df.columns,
            index=list(df.columns).index(auto_target)
            if auto_target in df.columns else 0
        )
    else:
        selected_target = st.selectbox(
            "Select target column manually:",
            options=df.columns
        )

    # -----------------------------------
    # Task Inference (Recompute Based on User Choice)
    # -----------------------------------
    task_type = infer_task_type(df, selected_target)

    st.write("📌 Detected Task Type:", task_type)

    # -----------------------------------
    # Let User Override Task
    # -----------------------------------
    task_options = [
        "binary_classification",
        "multiclass_classification",
        "regression",
        "unsupervised"
    ]

    task_type = st.selectbox(
        "Confirm or change task type:",
        options=task_options,
        index=task_options.index(task_type)
        if task_type in task_options else 0
    )

    st.markdown("---")

    # -----------------------------------
    # Model Family Recommendation
    # -----------------------------------
    st.subheader("🤖 Model Family Recommendation")

    model_recommendation = recommend_model_family(task_type, result["dataset_summary"])

    st.write("Recommended Primary:", model_recommendation.get("primary"))
    st.write("Recommended Secondary:", model_recommendation.get("secondary"))

    model_family_options = [
        "tree_based",
        "linear_model",
        "neural_network",
        "distance_based"
    ]

    selected_model_family = st.selectbox(
        "Select model family to prepare data for:",
        options=model_family_options,
        index=model_family_options.index(model_recommendation.get("primary"))
        if model_recommendation.get("primary") in model_family_options else 0
    )

    st.markdown("---")

    # -----------------------------------
    # FINAL DECISION SUMMARY
    # -----------------------------------
    st.header("📦 Final Model Preparation Plan")

    final_decision = {
        "target_column": selected_target,
        "task_type": task_type,
        "model_family": selected_model_family
    }

    st.json(final_decision)

    st.success("✅ Model direction finalized. Ready for preprocessing phase.")

    # Store in session state for later phases
    st.session_state["model_decision"] = final_decision


 # -----------------------------------
# EDA Section
# -----------------------------------
    st.markdown("---")
    st.header("📊 Exploratory Data Analysis")

    eda_summary = run_eda(df, selected_target)

    st.subheader("Dataset Signals Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Numerical Columns", len(eda_summary["numerical_columns"]))
        st.metric("Categorical Columns", len(eda_summary["categorical_columns"]))

    with col2:
        st.metric("High Missing Columns", len(eda_summary["high_missing_columns"]))
        st.metric("High Skew Columns", len(eda_summary["high_skew_columns"]))

    with col3:
        st.metric("Multicollinearity Score", eda_summary["multicollinearity_score"])
        st.metric("Needs Scaling", eda_summary["dataset_flags"]["needs_scaling"])

    st.markdown("---")

# Detailed Flags
    st.subheader("🚩 Dataset Risk Flags")

    st.json(eda_summary["dataset_flags"])

    st.markdown("---")

# Feature Stability (Advanced Signal)
    st.subheader("📉 Feature Stability Analysis")

    stability_df = pd.DataFrame.from_dict(
        eda_summary["feature_stability"],
        orient="index",
        columns=["Stability Score"]
    )

    stability_df = stability_df.sort_values(by="Stability Score", ascending=False)

# Risk categorization
    def categorize(score):
        if score < 0.3:
            return "🟢 Stable"
        elif score < 0.6:
            return "🟡 Moderate"
        else:
            return "🔴 High Risk"

    stability_df["Risk Level"] = stability_df["Stability Score"].apply(categorize)

    st.dataframe(stability_df, use_container_width=True)

# Store for preprocessing phase
    st.session_state["eda_summary"] = eda_summary

# ==========================================
# PREPROCESSING PLAN SECTION
# ==========================================

    import copy
    from src.preprocessing_planner import generate_preprocessing_plan
    from src.hitl_preprocessing import render_preprocessing_hitl

    st.markdown("---")
    st.header("🛠 Preprocessing Phase")

# -------------------------------------------------
# Generate Auto Plan (every rerun is fine)
# -------------------------------------------------

    auto_plan = generate_preprocessing_plan(
        eda_summary=eda_summary,
        task_type=task_type,
        model_family=selected_model_family,
        df=df
    )

# -------------------------------------------------
# Store Auto Plan (always refresh safely)
# -------------------------------------------------

    st.session_state["auto_preprocessing_plan"] = copy.deepcopy(auto_plan)

# -------------------------------------------------
# Initialize User Plan Only Once
# -------------------------------------------------

    if "user_preprocessing_plan" not in st.session_state:
        st.session_state["user_preprocessing_plan"] = copy.deepcopy(auto_plan)

# Always fetch AFTER initialization
    user_plan = st.session_state["user_preprocessing_plan"]

# -------------------------------------------------
# Render Human-in-the-Loop Controls
# -------------------------------------------------

    updated_plan = render_preprocessing_hitl(
        auto_plan=st.session_state["auto_preprocessing_plan"],
        user_plan=user_plan,
        task_type=task_type,
        model_family=selected_model_family
    )

# -------------------------------------------------
# Store Updated Plan
# -------------------------------------------------

    st.session_state["user_preprocessing_plan"] = updated_plan

# -------------------------------------------------
# Show Final Plan
# -------------------------------------------------

    st.markdown("### 📦 Final Preprocessing Plan")
    st.json(updated_plan)