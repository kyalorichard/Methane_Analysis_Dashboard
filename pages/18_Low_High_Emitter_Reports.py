
import io
import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import *
from analysis_engine.service_registry import get_service
build_emitter_cohorts = get_service("build_emitter_cohorts")
emitter_group_summary = get_service("emitter_group_summary")
emitter_profile = get_service("emitter_profile")
from analysis_engine.reporting import excel_bytes

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header(
    "Low & high emitter assessment",
    "Define phenotype-specific lower and upper percentile cohorts, inspect their profiles and export a reproducible report."
)
from analysis_engine.ui import render_workflow_shortcuts
render_workflow_shortcuts("Related emitter workflow", [
    ("Track emitter persistence across rounds", "pages/20_Longitudinal_Emitter_Tracking.py", "🔁"),
])
df = get_data()
roles = get_roles(df)
numeric = df.select_dtypes(include="number").columns.tolist()
preferred = roles.get("methane")
if preferred not in numeric:
    preferred = "mean_methane" if "mean_methane" in numeric else (numeric[0] if numeric else None)
if not numeric:
    st.error("No numeric variables are available. Select or map a numeric methane phenotype first.")
    st.stop()

st.subheader("Cohort definition")
c1, c2, c3 = st.columns([1.5, 1, 1])
with c1:
    phenotype = st.selectbox("Phenotype used to rank emitters", numeric,
                             index=numeric.index(preferred) if preferred in numeric else 0)
with c2:
    tail_percent = st.slider("Percentage in each tail", min_value=1, max_value=25, value=10, step=1,
                              help="For example, 10% selects the bottom 10% as low emitters and the top 10% as high emitters.")
with c3:
    animal_id = roles.get("animal_id")
    if animal_id not in df.columns:
        animal_id = None
    aggregation = st.selectbox("Repeated-measure aggregation", ["median", "mean"], index=0,
                               help="Applied within animal before percentile cut-points are calculated.")
    min_records = st.number_input("Minimum records per animal", min_value=1, value=1, step=1)

if animal_id:
    st.caption(f"Animal identifier detected: **{animal_id}**. Repeated records will be collapsed to one animal-level value before ranking.")
else:
    st.warning("No animal identifier was detected. Cohorts will be record-level, not animal-level; map AnimalID for defensible repeated-measure classification.")

try:
    cohorts, meta = build_emitter_cohorts(
        df, phenotype, tail_percent, animal_id, aggregation, int(min_records)
    )
except (ValueError, KeyError) as exc:
    st.error(str(exc))
    st.stop()

st.subheader("Cohort overview")
metric_row([
    ("Analysis units", f"{meta['n_units']:,}", meta["unit"]),
    ("Low emitters", f"{meta['n_low']:,}", f"Bottom {tail_percent}% by {phenotype}"),
    ("High emitters", f"{meta['n_high']:,}", f"Top {tail_percent}% by {phenotype}"),
    ("Intermediate", f"{meta['n_intermediate']:,}", "Remaining units"),
])
st.caption(
    f"Low-tail quantile cut-point: {meta['low_cutpoint']:.4g}; "
    f"high-tail quantile cut-point: {meta['high_cutpoint']:.4g}. "
    "Rank-based allocation is used to keep cohort sizes close to the requested percentage; tied values can be split at a boundary."
)

low_high = cohorts[cohorts["emitter_group"].isin(["Low emitter", "High emitter"])].copy()
fig = px.histogram(
    cohorts, x=phenotype, color="emitter_group", marginal="box", nbins=35,
    category_orders={"emitter_group": ["Low emitter", "Intermediate", "High emitter"]},
    title=f"{phenotype}: percentile-defined emitter cohorts"
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Low versus high emitter phenotype report")
summary = emitter_group_summary(cohorts, phenotype)
st.dataframe(summary, use_container_width=True)
if len(low_high):
    profile = emitter_profile(cohorts)
    st.markdown("**Numeric variable profiles**")
    numeric_profile = profile[profile.variable_type == "numeric"].copy()
    st.dataframe(numeric_profile, use_container_width=True)
    st.markdown("**Categorical composition**")
    categorical_profile = profile[profile.variable_type == "categorical_percent"].copy()
    if categorical_profile.empty:
        st.info("No categorical metadata variables are available for profile comparison.")
    else:
        st.dataframe(categorical_profile, use_container_width=True)
        candidate_cat = categorical_profile["variable"].dropna().unique().tolist()
        cat_var = st.selectbox("Visualise categorical composition", candidate_cat)
        chart_data = categorical_profile[categorical_profile.variable == cat_var]
        st.plotly_chart(px.bar(chart_data, x="category", y="percent", color="emitter_group",
                               barmode="group", title=f"{cat_var}: low versus high emitters"),
                        use_container_width=True)

st.subheader("Animal/record-level assignments")
display_cols = [c for c in [animal_id, "Breed", "Sex", "Round", phenotype, "n_measurements",
                             "phenotype_percentile", "emitter_group"] if c and c in cohorts.columns]
st.dataframe(cohorts[display_cols].sort_values(phenotype), use_container_width=True, height=360)

st.download_button(
    "Download emitter assignments (CSV)",
    cohorts.to_csv(index=False).encode("utf-8"),
    "low_high_emitter_assignments.csv", "text/csv"
)
sheets = {
    "Cohort_summary": summary,
    "Numeric_profiles": numeric_profile if len(low_high) else pd.DataFrame(),
    "Categorical_profiles": categorical_profile if len(low_high) else pd.DataFrame(),
    "Emitter_assignments": cohorts,
    "Configuration": pd.DataFrame([meta])
}
st.download_button(
    "Download complete emitter report (Excel)",
    excel_bytes(sheets),
    "low_high_emitter_report.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.info(
    "Interpretation: these are relative, dataset-specific percentile groups, not universal biological classes. "
    "The selected phenotype and tail percentage define the groups. Re-run the report separately by species, "
    "breed, sex or measurement protocol when those strata are scientifically justified. "
    "AUC/concentration proxies should not be interpreted as methane mass emissions without instrument calibration."
)
