"""Canonical independent-unit group comparison interface."""
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis_engine.ui import header, get_data, get_roles, numeric_cols, choose_col, render_sidebar_navigation
from analysis_engine.service_registry import get_service

render_sidebar_navigation()
header(
    "Group comparisons",
    "Compare methane phenotype distributions across biological or management groups using an explicit analysis unit.",
)

df = get_data().copy()
roles = get_roles(df)
nums = numeric_cols(df)
if not nums:
    st.error("No numeric phenotype variables are available.")
    st.stop()

animal_default = roles.get("animal_id")
phenotype = choose_col(df, "Phenotype outcome", roles.get("methane"), nums)
group_candidates = [c for c in df.columns if c != phenotype and 2 <= df[c].nunique(dropna=True) <= 30]
if not group_candidates:
    st.warning("No suitable grouping variable with 2–30 observed groups was found.")
    st.stop()
group = st.selectbox(
    "Grouping variable",
    group_candidates,
    index=group_candidates.index(roles.get("breed")) if roles.get("breed") in group_candidates else 0,
)

c1, c2, c3 = st.columns(3)
with c1:
    animal_col = st.selectbox("Animal identifier (optional)", ["—"] + list(df.columns),
                              index=(list(df.columns).index(animal_default) + 1) if animal_default in df.columns else 0)
with c2:
    aggregation = st.selectbox("Animal-level aggregation", ["median", "mean"], index=0)
with c3:
    method = st.selectbox("Statistical test", ["auto", "welch", "kruskal"], index=0)

use_animal = animal_col != "—"
if use_animal:
    analysis_df = df[[animal_col, group, phenotype]].copy()
    analysis_df[phenotype] = pd.to_numeric(analysis_df[phenotype], errors="coerce")
    # A subject assigned to multiple groups is not silently forced into one group.
    group_counts = analysis_df.dropna(subset=[animal_col, group]).groupby(animal_col)[group].nunique()
    ambiguous = group_counts[group_counts > 1].index
    if len(ambiguous):
        st.warning(f"{len(ambiguous):,} animals occur in more than one {group} category. These animals are excluded from the animal-level comparison; review study design before proceeding.")
        analysis_df = analysis_df[~analysis_df[animal_col].isin(ambiguous)]
    analysis_df = analysis_df.groupby([animal_col, group], as_index=False)[phenotype].agg(aggregation)
    unit_label = "animal-level"
else:
    analysis_df = df[[group, phenotype]].copy()
    analysis_df[phenotype] = pd.to_numeric(analysis_df[phenotype], errors="coerce")
    unit_label = "record-level"
    st.warning("No animal identifier selected. Records may not be independent; record-level tests are exploratory and can underestimate uncertainty when animals are measured repeatedly.")

analysis_df = analysis_df.dropna(subset=[group, phenotype])
if analysis_df.empty:
    st.error("No complete observations remain for this comparison.")
    st.stop()

st.caption(f"Analysis unit: {unit_label} · n = {len(analysis_df):,} · aggregation = {aggregation if use_animal else 'none'}")
summary = analysis_df.groupby(group, dropna=False)[phenotype].agg(
    n="count", mean="mean", sd="std", median="median", q1=lambda x: x.quantile(.25), q3=lambda x: x.quantile(.75)
).reset_index()
st.subheader("Group profile")
st.dataframe(summary, use_container_width=True, hide_index=True)
fig = px.box(analysis_df, x=group, y=phenotype, color=group, points="outliers", title=f"{phenotype} by {group}")
fig.update_layout(template="plotly_white", height=420, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

if st.button("Run group comparison", type="primary"):
    try:
        result = get_service("group_comparison")(analysis_df, phenotype, group, method=method)
        st.session_state["canonical_group_comparison"] = {
            "result": result, "phenotype": phenotype, "group": group,
            "analysis_unit": unit_label, "aggregation": aggregation if use_animal else None,
        }
    except Exception as exc:
        st.error(f"Comparison could not be estimated: {type(exc).__name__}: {exc}")

saved = st.session_state.get("canonical_group_comparison")
if saved and saved.get("phenotype") == phenotype and saved.get("group") == group:
    result = saved["result"]
    st.subheader("Inferential result")
    m1, m2, m3 = st.columns(3)
    m1.metric("Method", result.get("method", "—"))
    m2.metric("P-value", f"{result['p_value']:.4g}" if pd.notna(result.get("p_value")) else "Not estimable")
    m3.metric("Independent units", f"{sum(result.get('n', [])):,}")
    st.json(result)
    if result.get("pairwise_mann_whitney"):
        st.subheader("Pairwise comparisons (BH-adjusted)")
        st.dataframe(pd.DataFrame(result["pairwise_mann_whitney"]), use_container_width=True, hide_index=True)
    st.caption("These tests are not a substitute for mixed-effects or other design-based models when covariates, clustering, repeated measures or complex sampling must be modelled.")

st.info("Scientific interpretation: report the analysis unit, group sample sizes, effect size, uncertainty and multiple-testing procedure. Group differences are associations, not causal effects.")
