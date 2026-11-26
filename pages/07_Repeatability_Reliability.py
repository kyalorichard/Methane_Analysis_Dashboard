
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.settings_config import load_active_settings
from analysis_engine.service_registry import get_service

render_sidebar_navigation()
_cfg = load_active_settings(st.session_state)
_rep_cfg = _cfg.get("repeatability", {})

header(
    'Repeatability & reliability',
    'Quantify within-animal consistency across repeated rounds or measurement sessions.'
)

# ---------------------------------------------------------
# 1. LOAD DATA AND IDENTIFY VARIABLES
# ---------------------------------------------------------

df = get_data()
r = get_roles(df)

animal_default = _rep_cfg.get('animal_column') if _rep_cfg.get('animal_column') in df.columns else r.get('animal_id')
animal = animal_default
round_default = _rep_cfg.get('occasion_column') if _rep_cfg.get('occasion_column') in df.columns else r.get('round')
roundc = round_default
nums = numeric_cols(df)

if not animal or not roundc:
    st.error('Map both Animal ID and Round in Data Management or dataset configuration.')
    st.stop()

out = choose_col(
    df,
    'Phenotype outcome',
    r.get('methane'),
    nums
)

if not out:
    st.error('Select a valid numerical phenotype outcome.')
    st.stop()

# ---------------------------------------------------------
# 2. PREPARE DATA
# ---------------------------------------------------------

try:
    # Shared panel construction prevents different duplicate-cell handling across pages.
    p, panel_audit = get_service("build_reliability_panel")(
        df, animal, roundc, out, aggregation="median"
    )
except Exception as exc:
    st.warning(f'Unable to construct repeated-measurement panel: {exc}')
    st.stop()

# ---------------------------------------------------------
# 3. SUMMARY METRICS
# ---------------------------------------------------------

animals_with_repeats = int(
    (p.notna().sum(axis=1) >= 2).sum()
)

complete_animals = int(
    p.dropna().shape[0]
)

st.caption(f"Duplicate subject-round rows aggregated: {panel_audit['duplicate_subject_occasion_rows_aggregated']:,}.")

metric_row([
    (
        'ANIMALS WITH REPEATS',
        f'{animals_with_repeats:,}',
        'At least two observed rounds'
    ),
    (
        'ROUNDS',
        str(p.shape[1]),
        'Observed round categories'
    ),
    (
        'COMPLETE ANIMALS',
        f'{complete_animals:,}',
        'Complete across displayed rounds'
    )
])

# ---------------------------------------------------------
# 4. WITHIN-ANIMAL TRAJECTORIES
# ---------------------------------------------------------

if p.shape[1] >= 2:

    st.subheader('Within-animal trajectories')

    # Retain animals with at least two observed measurements.
    # Do not require completeness across every round.
    p_plot = p.loc[
        p.notna().sum(axis=1) >= 2
    ].head(150)

    if not p_plot.empty:

        fig = go.Figure()

        # Use the actual round categories as x-axis positions.
        rounds = [str(x) for x in p_plot.columns]

        for animal_id, row in p_plot.iterrows():

            values = pd.to_numeric(
                row,
                errors='coerce'
            )

            valid = values.notna()

            if valid.sum() < 2:
                continue

            x_values = [
                rounds[i]
                for i, is_valid in enumerate(valid)
                if is_valid
            ]

            y_values = values[valid].tolist()

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode='lines+markers',
                    line=dict(width=1),
                    marker=dict(size=4),
                    opacity=0.20,
                    name=str(animal_id),
                    showlegend=False,
                    hovertemplate=(
                        'Animal: ' + str(animal_id) +
                        '<br>Round: %{x}' +
                        '<br>Phenotype: %{y:.3f}' +
                        '<extra></extra>'
                    )
                )
            )

        fig.update_layout(
            title='Within-animal phenotype trajectories',
            xaxis_title='Measurement round',
            yaxis_title=str(out),
            template='plotly_white',
            height=550,
            hovermode='closest'
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.caption(
            f'Displaying up to 150 animals with at least two '
            f'observed measurements. Total eligible animals: '
            f'{animals_with_repeats:,}.'
        )

    else:
        st.info(
            'Insufficient repeated observations for trajectory plotting.'
        )

    st.info("Formal repeatability estimation is centralised in the Reliability & Agreement workspace. This page is retained for within-animal trajectory visualisation only.")
    st.page_link("pages/33_Reliability_and_Agreement.py", label="Open canonical reliability and agreement analysis", icon="📏")
