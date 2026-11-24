import json
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis_engine.release6 import estimate_repeatability_icc, within_between_variability, bland_altman_summary

st.set_page_config(page_title="Reliability and Agreement", page_icon="📏", layout="wide")
st.title("Reliability, Repeatability & Measurement Agreement")
st.caption("Release 6.1 · Subject-level reliability, within/between-animal variability and paired-method agreement")

if "data" not in st.session_state:
    st.info("Load a dataset using the platform data-management workflow first.")
    st.stop()

df = st.session_state["data"]
all_cols = list(df.columns)
numeric = list(df.select_dtypes(include="number").columns)

st.header("1. Repeatability and intraclass correlation")
st.markdown("Reshape repeated measurements into a subject × occasion panel. Duplicate subject–occasion records are aggregated using the selected summary statistic.")
if len(numeric) < 1 or len(all_cols) < 2:
    st.warning("The loaded dataset does not contain enough variables for this analysis.")
else:
    c1, c2, c3 = st.columns(3)
    animal = c1.selectbox("Subject / animal identifier", all_cols, key="rel_animal")
    outcome = c2.selectbox("Phenotype", numeric, key="rel_outcome")
    occasion = c3.selectbox("Measurement occasion", [c for c in all_cols if c != animal], key="rel_occasion")
    agg = st.selectbox("Aggregate duplicate subject–occasion records", ["median", "mean"], index=0)
    icc_model = st.selectbox("ICC design", ["ICC1", "ICC2", "ICC3"], format_func=lambda x: {
        "ICC1": "ICC(1): one-way random effects",
        "ICC2": "ICC(2): two-way random, absolute agreement",
        "ICC3": "ICC(3): two-way mixed, consistency"
    }[x])
    boots = st.slider("Subject-level bootstrap replicates", 200, 3000, 1000, 200)
    conf = st.select_slider("Confidence level", options=[0.90, 0.95, 0.99], value=0.95)
    if st.button("Estimate repeatability and ICC", type="primary"):
        try:
            d = df[[animal, occasion, outcome]].copy()
            d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
            d = d.dropna(subset=[animal, occasion, outcome])
            panel = d.pivot_table(index=animal, columns=occasion, values=outcome, aggfunc=agg)
            complete = panel.dropna(axis=0, how="any")
            if complete.shape[1] < 2:
                raise ValueError("At least two measurement occasions are needed.")
            icc = estimate_repeatability_icc(complete, model=icc_model, n_boot=boots, confidence=conf)
            var = within_between_variability(complete)
            st.session_state["r61_icc_result"] = icc
            st.session_state["r61_variance_result"] = var
            st.session_state["r61_panel"] = complete
            st.session_state["r61_panel_shape"] = (int(panel.shape[0]), int(panel.shape[1]), int(complete.shape[0]))
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
    if st.session_state.get("r61_icc_result"):
        r = st.session_state["r61_icc_result"]
        v = st.session_state["r61_variance_result"]
        shape = st.session_state["r61_panel_shape"]
        a, b, c = st.columns(3)
        a.metric("Single-measure ICC", f"{r['icc_single']:.3f}", help="Reliability of one measurement occasion.")
        b.metric("Average-measure ICC", f"{r['icc_average']:.3f}", help="Reliability of the average across occasions.")
        c.metric("Complete subjects", f"{r['n_subjects']:,}")
        st.write(f"**{conf:.0%} subject-bootstrap CI for single-measure ICC:** {r['icc_single_ci_low']:.3f} to {r['icc_single_ci_high']:.3f}")
        st.caption(r["interpretation"])
        st.caption(f"Panel construction: {shape[0]:,} subjects initially; {shape[2]:,} complete subjects across {shape[1]} occasions. Complete-case ICC can change the target population if missingness is informative.")
        st.subheader("Within- and between-subject variance")
        st.dataframe(pd.DataFrame([
            {"Component": "Between-subject", "Variance": v["between_subject_variance"], "Fraction": v["between_subject_fraction"]},
            {"Component": "Within-subject", "Variance": v["within_subject_variance"], "Fraction": v["within_subject_fraction"]}
        ]), use_container_width=True, hide_index=True)
        st.caption(v["note"])
        st.warning(r["caution"])
        st.download_button("Download ICC and variance results", json.dumps({"icc": r, "variance": v}, indent=2), "repeatability_icc_results.json", "application/json")

st.divider()
st.header("2. Bland–Altman agreement between two measurement methods")
st.markdown("Use paired measurements of the same biological quantity and compatible units. Correlation alone is not evidence of agreement.")
if len(numeric) >= 2:
    x1, x2 = st.columns(2)
    method_a = x1.selectbox("Method / occasion A", numeric, key="ba_a")
    method_b = x2.selectbox("Method / occasion B", [c for c in numeric if c != method_a], key="ba_b")
    ba_boot = st.slider("Bland–Altman bootstrap replicates", 200, 3000, 1000, 200, key="ba_boot")
    if st.button("Calculate agreement"):
        try:
            result = bland_altman_summary(df[method_a], df[method_b], n_boot=ba_boot)
            st.session_state["r61_ba_result"] = result
            pair = pd.DataFrame({"mean": (pd.to_numeric(df[method_a], errors="coerce") + pd.to_numeric(df[method_b], errors="coerce"))/2,
                                 "difference": pd.to_numeric(df[method_a], errors="coerce") - pd.to_numeric(df[method_b], errors="coerce")}).dropna()
            st.session_state["r61_ba_plot"] = pair
        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
    if st.session_state.get("r61_ba_result"):
        r = st.session_state["r61_ba_result"]
        a, b, c = st.columns(3)
        a.metric("Mean bias (A − B)", f"{r['bias_first_minus_second']:.3f}")
        b.metric("Lower limit of agreement", f"{r['lower_limit_of_agreement']:.3f}")
        c.metric("Upper limit of agreement", f"{r['upper_limit_of_agreement']:.3f}")
        st.write(f"Bias {r['ci_level']:.0%} CI: {r['bias_ci'][0]:.3f} to {r['bias_ci'][1]:.3f}")
        p = st.session_state["r61_ba_plot"]
        fig = px.scatter(p, x="mean", y="difference", labels={"mean": "Mean of paired measurements", "difference": "A − B"}, title="Bland–Altman plot")
        fig.add_hline(y=r["bias_first_minus_second"], line_dash="dash", annotation_text="Mean bias")
        fig.add_hline(y=r["lower_limit_of_agreement"], line_dash="dot", annotation_text="Lower LoA")
        fig.add_hline(y=r["upper_limit_of_agreement"], line_dash="dot", annotation_text="Upper LoA")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(r["note"])
        st.download_button("Download agreement results", json.dumps(r, indent=2), "bland_altman_results.json", "application/json")
else:
    st.info("At least two numeric variables are required for paired-method agreement.")

st.divider()
st.caption("Interpret ICC according to the measurement design: absolute agreement versus consistency, fixed versus random occasions, and single versus average measurements. ICC is population-dependent and is not heritability. For nested animals within herds/sites, consider the highest independent sampling unit when constructing confidence intervals.")
