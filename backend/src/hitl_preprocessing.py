import streamlit as st
import copy


def render_preprocessing_hitl(auto_plan, user_plan, task_type, model_family):

    # ----------------------------------------
    # Initialize Session Plans Safely
    # ----------------------------------------

    if "auto_preprocessing_plan" not in st.session_state:
        st.session_state["auto_preprocessing_plan"] = copy.deepcopy(auto_plan)

    if "user_preprocessing_plan" not in st.session_state:
        st.session_state["user_preprocessing_plan"] = copy.deepcopy(auto_plan)

    auto_plan = st.session_state["auto_preprocessing_plan"]
    user_plan = st.session_state["user_preprocessing_plan"]

    st.header("🛠 Human-in-the-Loop Preprocessing")

    # =====================================================
    # 🔧 IMPUTATION
    # =====================================================

    st.subheader("🔧 Imputation")

    options = ["mean", "median", "most_frequent", "constant", "drop"]

    for col in list(user_plan.get("imputation", {}).keys()):

        current_cfg = user_plan["imputation"].get(col, {})
        auto_cfg = auto_plan["imputation"].get(col, {})

        current_method = current_cfg.get("method", "mean") if isinstance(current_cfg, dict) else current_cfg
        auto_method = auto_cfg.get("method") if isinstance(auto_cfg, dict) else auto_cfg

        if current_method not in options:
            current_method = "mean"

        new_method = st.selectbox(
            f"{col}",
            options,
            index=options.index(current_method),
            key=f"imp_{col}"
        )

        reason = auto_cfg.get("reason", "") if isinstance(auto_cfg, dict) else ""

        if reason:
            st.caption(f"🤖 Auto: {reason}")

        # ---- Apply change safely ----

        if new_method == "drop":
            if col not in user_plan["drop_columns"]:
                user_plan["drop_columns"].append(col)
            user_plan["imputation"].pop(col, None)
        else:
            user_plan["imputation"][col] = {
                "method": new_method,
                "reason": reason
            }
            if col in user_plan["drop_columns"]:
                user_plan["drop_columns"].remove(col)

        if auto_method != new_method:
            st.caption(f"⚡ Changed from auto: {auto_method}")

    # =====================================================
    # 🏷 ENCODING
    # =====================================================

    st.subheader("🏷 Encoding")

    encoding_options = ["onehot", "target", "frequency", "label", "drop"]

    for col in list(user_plan.get("encoding", {}).keys()):

        current_cfg = user_plan["encoding"].get(col, {})
        auto_cfg = auto_plan["encoding"].get(col, {})

        current_method = current_cfg.get("method", "onehot") if isinstance(current_cfg, dict) else current_cfg
        auto_method = auto_cfg.get("method") if isinstance(auto_cfg, dict) else auto_cfg

        if current_method not in encoding_options:
            current_method = "onehot"

        new_method = st.selectbox(
            f"{col}",
            encoding_options,
            index=encoding_options.index(current_method),
            key=f"enc_{col}"
        )

        reason = auto_cfg.get("reason", "") if isinstance(auto_cfg, dict) else ""

        if reason:
            st.caption(f"🤖 Auto: {reason}")

        if new_method == "drop":
            if col not in user_plan["drop_columns"]:
                user_plan["drop_columns"].append(col)
            user_plan["encoding"].pop(col, None)
        else:
            user_plan["encoding"][col] = {
                "method": new_method,
                "reason": reason
            }
            if col in user_plan["drop_columns"]:
                user_plan["drop_columns"].remove(col)

        if auto_method != new_method:
            st.caption(f"⚡ Changed from auto: {auto_method}")

    # =====================================================
    # ⚖ Scaling
    # =====================================================
    st.subheader("⚖ Scaling")

    scaling_options = ["standard", "minmax", "robust", "none"]

    auto_scaling_cfg = auto_plan.get("scaling")
    user_scaling_cfg = user_plan.get("scaling")

    auto_scaling = (
        auto_scaling_cfg.get("method")
        if isinstance(auto_scaling_cfg, dict)
        else "none"
    )

    current_scaling = (
        user_scaling_cfg.get("method")
        if isinstance(user_scaling_cfg, dict)
        else "none"
    )

    if current_scaling not in scaling_options:
        current_scaling = "none"

    new_scaling = st.selectbox(
        "Scaling Strategy",
        scaling_options,
        index=scaling_options.index(current_scaling),
        key="scaling_control"
    )

    if new_scaling == "none":
        user_plan["scaling"] = None
    else:
        user_plan["scaling"] = {
            "method": new_scaling,
            "reason": auto_scaling_cfg.get("reason", "")
            if isinstance(auto_scaling_cfg, dict)
            else ""
        }

    if auto_scaling != new_scaling:
        st.caption(f"⚡ Changed from auto: {auto_scaling}")
    # =====================================================
    # 🧬 Feature Selection
    # =====================================================

        st.subheader("🧬 Feature Selection")

    fs_options = ["none", "variance", "mutual_info", "l1"]

    auto_fs_cfg = auto_plan.get("feature_selection")
    user_fs_cfg = user_plan.get("feature_selection")

    auto_fs = (
        auto_fs_cfg.get("method")
        if isinstance(auto_fs_cfg, dict)
        else "none"
    )

    current_fs = (
        user_fs_cfg.get("method")
        if isinstance(user_fs_cfg, dict)
        else "none"
    )

    if current_fs not in fs_options:
        current_fs = "none"

    new_fs = st.selectbox(
        "Feature Selection Method",
        fs_options,
        index=fs_options.index(current_fs),
        key="fs_control"
    )

    if new_fs == "none":
        user_plan["feature_selection"] = None
    else:
        user_plan["feature_selection"] = {
            "method": new_fs,
            "reason": auto_fs_cfg.get("reason", "")
            if isinstance(auto_fs_cfg, dict)
            else ""
        }

    if auto_fs != new_fs:
        st.caption(f"⚡ Changed from auto: {auto_fs}")
    # =====================================================
    # ⚖ Class Imbalance
    # =====================================================

    if task_type != "regression":

        st.subheader("⚖ Imbalance Handling")

        imbalance_options = ["none", "class_weight", "smote"]

        auto_imb_cfg = auto_plan.get("imbalance_handling")
        user_imb_cfg = user_plan.get("imbalance_handling")

        auto_imb = (
            auto_imb_cfg.get("method")
            if isinstance(auto_imb_cfg, dict)
            else "none"
        )

        current_imb = (
            user_imb_cfg.get("method")
            if isinstance(user_imb_cfg, dict)
            else "none"
        )

    if current_imb not in imbalance_options:
        current_imb = "none"

    new_imb = st.selectbox(
        "Imbalance Strategy",
        imbalance_options,
        index=imbalance_options.index(current_imb),
        key="imb_control"
    )

    if new_imb == "none":
        user_plan["imbalance_handling"] = None
    else:
        user_plan["imbalance_handling"] = {
            "method": new_imb,
            "reason": auto_imb_cfg.get("reason", "")
            if isinstance(auto_imb_cfg, dict)
            else ""
        }

    if auto_imb != new_imb:
        st.caption(f"⚡ Changed from auto: {auto_imb}")
    # ----------------------------------------
    # Final Plan Preview
    # ----------------------------------------

    st.markdown("---")
    st.subheader("📦 Final Preprocessing Plan")

    st.json(user_plan)

    return user_plan