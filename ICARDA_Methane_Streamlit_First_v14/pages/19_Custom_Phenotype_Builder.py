
import json
import streamlit as st
import pandas as pd
from analysis_engine.ui import *
from analysis_engine.phenotype_builder import create_derived_phenotype, FormulaError

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header("Custom phenotype builder", "Create new analysis variables from transparent, user-defined mathematical formulas.")
df = get_data()
st.markdown("Define a new phenotype using existing dataset columns and supported mathematical functions. The source columns are never overwritten.")
st.caption("Use column names exactly as shown. Formula evaluation is restricted to approved arithmetic and functions; arbitrary Python code is not executed.")

with st.expander("Formula examples", expanded=True):
    st.code("AUC_full / full_duration_sec", language="python")
    st.code("(n_eruct / full_duration_sec) * 60", language="python")
    st.code("log1p(mean_methane)", language="python")
    st.code("clip(AUC_per_sec, 0, 100)", language="python")
    st.code("where(weight > 0, mean_methane / weight, 0)", language="python")
    st.caption("Supported functions: abs, sqrt, log, log1p, exp, minimum, maximum, clip and where. Arithmetic: +, -, *, /, ** and %.")

with st.expander("Available dataset variables"):
    st.write(", ".join(map(str, df.columns)))
    st.dataframe(pd.DataFrame({"variable":df.columns, "data_type":[str(x) for x in df.dtypes],
                               "missing_percent":(df.isna().mean()*100).round(2).values}),
                 use_container_width=True)

st.subheader("Define phenotype")
with st.form("phenotype_builder_form"):
    name = st.text_input("New phenotype name", placeholder="e.g. methane_per_kg")
    formula = st.text_area("Formula", placeholder="mean_methane / weight", height=100)
    description = st.text_input("Scientific definition / interpretation",
                                placeholder="Mean methane signal normalised by liveweight")
    units = st.text_input("Units", placeholder="e.g. instrument units per kg")
    submitted = st.form_submit_button("Validate and generate phenotype", type="primary")

if submitted:
    try:
        updated = create_derived_phenotype(df, name, formula)
        st.session_state["data"] = updated
        definitions = st.session_state.get("phenotype_definitions", [])
        definitions = [x for x in definitions if x.get("name") != name.strip()]
        definitions.append({"name":name.strip(),"formula":formula.strip(),
                            "description":description.strip(),"units":units.strip()})
        st.session_state["phenotype_definitions"] = definitions
        st.success(f"Created '{name.strip()}' and added it to the active dataset. It is now available in downstream analysis modules.")
        vals = pd.to_numeric(updated[name.strip()], errors="coerce")
        metric_row([("Valid values", f"{vals.notna().sum():,}", "Non-missing derived values"),
                    ("Missing values", f"{vals.isna().sum():,}", "Includes missing inputs and undefined operations"),
                    ("Mean", f"{vals.mean():.4g}" if vals.notna().any() else "—", units or "Unspecified units"),
                    ("SD", f"{vals.std():.4g}" if vals.notna().any() else "—", "Standard deviation")])
        st.dataframe(vals.describe(percentiles=[.05,.25,.5,.75,.95]).to_frame(name=name.strip()),
                     use_container_width=True)
    except (FormulaError, Exception) as exc:
        st.error(f"Could not generate phenotype: {exc}")

st.subheader("Phenotype formula registry")
definitions = st.session_state.get("phenotype_definitions", [])
if definitions:
    st.dataframe(pd.DataFrame(definitions), use_container_width=True)
    st.download_button("Download phenotype definitions (JSON)",
                       json.dumps(definitions, indent=2).encode("utf-8"),
                       "custom_phenotype_definitions.json","application/json")
else:
    st.info("No custom phenotype formulas have been registered in this session.")
st.warning("Custom variables are retained in the active Streamlit session. Download the dataset and formula registry to preserve them outside this session. Check dimensional consistency, units, denominator validity and biological interpretation before scientific use.")
