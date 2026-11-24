
import streamlit as st
import pandas as pd
import plotly.express as px
from analysis_engine.ui import *
from analysis_engine.emitter_tracking import classify_emitters_by_round, emitter_persistence_summary

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header("Longitudinal emitter tracking", "Assess whether animals retain low-, intermediate- or high-emitter status across recording rounds.")
df = get_data()
roles = get_roles(df)
animal_default = roles.get("animal_id")
animal_options = df.columns.tolist()
animal_col = st.selectbox("Animal identifier", animal_options,
                          index=animal_options.index(animal_default) if animal_default in animal_options else 0)
round_candidates = [c for c in df.columns if c.lower() in ["round","visit","session","sampling_round","log_day","date","file_date"]]
round_default = roles.get("round")
if round_default not in df.columns and round_candidates:
    round_default = round_candidates[0]
round_col = st.selectbox("Recording round / visit", df.columns.tolist(),
                         index=df.columns.get_loc(round_default) if round_default in df.columns else 0)
numeric = df.select_dtypes(include="number").columns.tolist()
preferred = roles.get("methane")
if preferred not in numeric:
    preferred = "mean_methane" if "mean_methane" in numeric else (numeric[0] if numeric else None)
if not numeric:
    st.error("No numeric phenotype variables found.")
    st.stop()
phenotype = st.selectbox("Phenotype for classification", numeric,
                         index=numeric.index(preferred) if preferred in numeric else 0)
c1,c2 = st.columns(2)
with c1:
    tail_percent = st.slider("Low/high tail percentage per round",1,25,10)
with c2:
    aggregation = st.selectbox("Within-animal-round aggregation",["median","mean"])
min_records = st.number_input("Minimum records per animal per round", min_value=1, value=1, step=1)

try:
    assignments, thresholds = classify_emitters_by_round(
        df, animal_col, round_col, phenotype, tail_percent, aggregation, int(min_records)
    )
    transitions, persistence = emitter_persistence_summary(assignments, animal_col, round_col)
except Exception as exc:
    st.error(f"Unable to classify longitudinal emitters: {exc}")
    st.stop()

st.subheader("Round-specific classification")
st.caption("Percentile cut-points are recalculated independently within each round. This tracks relative rank within a round, not absolute stability of methane output.")
st.dataframe(thresholds, use_container_width=True)
long_counts = assignments.groupby([round_col,"emitter_group"]).size().reset_index(name="n_animals")
st.plotly_chart(px.bar(long_counts,x=round_col,y="n_animals",color="emitter_group",barmode="stack",
                       category_orders={"emitter_group":["Low emitter","Intermediate","High emitter"]},
                       title="Emitter classification by round"),use_container_width=True)

st.subheader("Classification persistence and transitions")
if transitions.empty:
    st.info("At least two recording rounds with overlapping animals are required to estimate transitions.")
else:
    st.dataframe(transitions, use_container_width=True)
    for (r1,r2), part in transitions.groupby(["from_round","to_round"],sort=False):
        matrix = part.pivot(index="from_group",columns="to_group",values="percent_within_origin_group").fillna(0)
        st.markdown(f"**{r1} → {r2}**")
        st.plotly_chart(px.imshow(matrix, text_auto=".1f", aspect="auto", color_continuous_scale="Blues",
                                  labels=dict(x="Next-round group",y="Current-round group",color="% within group")),
                        use_container_width=True)
st.dataframe(persistence, use_container_width=True)
st.subheader("Animal-level longitudinal assignments")
st.dataframe(assignments, use_container_width=True, height=350)
st.download_button("Download longitudinal classifications (CSV)",
                   assignments.to_csv(index=False).encode("utf-8"),
                   "longitudinal_emitter_classifications.csv","text/csv")
st.download_button("Download round thresholds (CSV)",
                   thresholds.to_csv(index=False).encode("utf-8"),
                   "longitudinal_emitter_thresholds.csv","text/csv")
st.info("Interpretation: consistent high/low status across rounds is evidence of rank persistence under the chosen phenotype and relative thresholds. It is not heritability, a causal trait, or absolute emission stability. Consider ICC/repeatability analysis and a mixed-effects model alongside these descriptive transitions.")
