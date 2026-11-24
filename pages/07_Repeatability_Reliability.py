
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation

render_sidebar_navigation()

header(
    'Repeatability & reliability',
    'Quantify within-animal consistency across repeated rounds or measurement sessions.'
)

# ---------------------------------------------------------
# 1. LOAD DATA AND IDENTIFY VARIABLES
# ---------------------------------------------------------

df = get_data()
r = get_roles(df)

animal = r.get('animal_id')
roundc = r.get('round')
nums = numeric_cols(df)

if not animal or not roundc:
    st.error('Map both Animal ID and Round in Data Management.')
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

d = df[[animal, roundc, out]].copy()

d[out] = pd.to_numeric(d[out], errors='coerce')

d = d.dropna(subset=[animal, roundc, out])

if d.empty:
    st.warning('No valid repeated-measurement observations available.')
    st.stop()

# One median phenotype value per animal and round
p = d.pivot_table(
    index=animal,
    columns=roundc,
    values=out,
    aggfunc='median'
)

# ---------------------------------------------------------
# 3. SUMMARY METRICS
# ---------------------------------------------------------

animals_with_repeats = int(
    (p.notna().sum(axis=1) >= 2).sum()
)

complete_animals = int(
    p.dropna().shape[0]
)

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

    # -----------------------------------------------------
    # 5. EXPLORATORY ICC(1,1)
    # -----------------------------------------------------

    st.subheader('Repeatability estimation')

    # Balanced complete-case observations
    q = p.dropna().astype(float)

    n = q.shape[0]
    k = q.shape[1]

    if n >= 3 and k >= 2:

        values = q.to_numpy(dtype=float)

        grand_mean = values.mean()

        animal_means = values.mean(axis=1)

        ms_between = (
            k * np.sum((animal_means - grand_mean) ** 2)
            / (n - 1)
        )

        ms_within = (
            np.sum(
                (values - animal_means[:, None]) ** 2
            )
            / (n * (k - 1))
        )

        denominator = (
            ms_between + (k - 1) * ms_within
        )

        if denominator > 0:

            icc = (
                ms_between - ms_within
            ) / denominator

        else:
            icc = np.nan

        if np.isfinite(icc):

            st.metric(
                'Exploratory ICC(1,1)',
                f'{icc:.3f}'
            )

            st.caption(
                f'Balanced complete-case one-way random-effects '
                f'ICC(1,1): n={n:,} animals and k={k} rounds.'
            )

        else:
            st.info(
                'ICC is not estimable because the variance '
                'components produce a zero denominator.'
            )

        st.info(
            'This is an exploratory one-way random-effects ICC. '
            'For formal scientific reporting, select an ICC model '
            'appropriate to the measurement design and calculate '
            'confidence intervals.'
        )

    else:

        st.info(
            'At least three animals with complete observations '
            'across two or more rounds are required for this '
            'exploratory ICC calculation.'
        )

else:

    st.info(
        'At least two measurement rounds are required '
        'to assess repeatability.'
    )

# ---------------------------------------------------------
# 6. SCIENTIFIC INTERPRETATION
# ---------------------------------------------------------

st.warning(
    'Repeatability is not heritability. This descriptive ICC '
    'does not independently account for session, assessor, '
    'environmental, physiological or other systematic effects.'
)
