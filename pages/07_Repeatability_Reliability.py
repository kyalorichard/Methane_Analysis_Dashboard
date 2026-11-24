import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Repeatability & reliability','Quantify within-animal consistency across repeated rounds or measurement sessions.')
df=get_data();r=get_roles(df);animal=r.get('animal_id');roundc=r.get('round');nums=numeric_cols(df)
if not animal or not roundc: st.error('Map both Animal ID and Round in Data Management.');st.stop()
out=choose_col(df,'Phenotype outcome',r.get('methane'),nums)
d=df[[animal,roundc,out]].copy();d[out]=pd.to_numeric(d[out],errors='coerce');d=d.dropna()
p=d.pivot_table(index=animal,columns=roundc,values=out,aggfunc='median')
metric_row([('ANIMALS WITH REPEATS',f'{int((p.notna().sum(axis=1)>=2).sum()):,}','At least two observed rounds'),('ROUNDS',str(p.shape[1]),'Observed round categories'),('PAIRED ANIMALS',f'{int(p.dropna().shape[0]):,}','Complete across all displayed rounds')])
if p.shape[1]>=2:
    # Within-animal trajectories
    st.subheader("Within-animal trajectories")

    # Remove incomplete observations
    p_clean = p.dropna().head(150).copy()

    if not p_clean.empty:

        # Convert animal identifiers into a regular column
        p_plot = p_clean.reset_index()

        # Ensure the identifier column exists
        if animal not in p_plot.columns:
            p_plot = p_plot.rename(
                columns={p_plot.columns[0]: animal}
            )

        # Convert repeated measurements into long format
        p_long = p_plot.melt(
            id_vars=[animal],
            var_name="measurement",
            value_name="value"
        )

        # Ensure measurements are numeric
        p_long["value"] = pd.to_numeric(
            p_long["value"], errors="coerce"
        )

        p_long = p_long.dropna(subset=["value"])

        if not p_long.empty:
            fig = px.line(
                p_long,
                x="measurement",
                y="value",
                color=animal,
                title="Within-animal trajectories (first 150 complete animals)",
                opacity=0.18
            )

            fig.update_layout(
                xaxis_title="Measurement",
                yaxis_title="Phenotype value",
                legend_title="Animal ID"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )
        else:
            st.info("No valid numeric measurements available for plotting.")
    else:
        st.info("Insufficient complete animal observations for trajectory plotting.")

    # One-way random effects ICC(1,1) on balanced complete cases, explicitly labelled exploratory.
    q=p.dropna();k=q.shape[1];n=q.shape[0]
    if n>=3 and k>=2:
        grand=q.values.mean(); rowm=q.mean(axis=1).values; colm=q.mean(axis=0).values
        msb=k*np.sum((rowm-grand)**2)/(n-1); msw=np.sum((q.values-rowm[:,None])**2)/(n*(k-1))
        icc=(msb-msw)/(msb+(k-1)*msw) if (msb+(k-1)*msw)!=0 else np.nan
        st.metric('Exploratory ICC(1,1)',f'{icc:.3f}' if np.isfinite(icc) else 'Not estimable')
        st.caption(f'Balanced complete-case one-way random-effects ICC; n={n} animals, k={k} rounds. For formal reporting, select an ICC model matching the measurement design and obtain confidence intervals.')
    else: st.info('Insufficient balanced repeated observations for an ICC estimate.')
else: st.info('At least two rounds are required.')
st.warning('Repeatability is not heritability. This descriptive ICC does not account for all possible session, assessor or environmental effects.')
