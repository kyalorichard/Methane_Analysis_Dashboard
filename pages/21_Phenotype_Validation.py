import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from analysis_engine.ui import header, get_data, metric_row, numeric_cols
from analysis_engine.phenotype_validation import distribution_diagnostics, group_profile, repeated_measure_diagnostics, correlate_with_covariate

from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Phenotype discovery & validation', 'A structured diagnostic workflow for evaluating candidate phenotypes before scientific interpretation or publication.')
df = get_data()
nums = numeric_cols(df)
if not nums:
    st.error('No numeric phenotype columns are available.'); st.stop()

st.info('This workbench provides exploratory statistical evidence. Biological validity requires a prespecified construct, protocol documentation, dimensional consistency and domain-expert review. Repeatability is not heritability; association is not causation.')
phenotype = st.selectbox('Candidate phenotype', nums, index=nums.index('mean_methane') if 'mean_methane' in nums else 0)

st.subheader('1. Distribution, completeness and data quality')
diag = distribution_diagnostics(df, phenotype)
metric_row([('Valid observations', f"{diag['n_valid']:,}", 'Numeric, non-missing records'), ('Missing', f"{diag['missing_pct']:.2f}%", f"{diag['n_missing']:,} records"), ('Mean ± SD', f"{diag['mean']:.3g} ± {diag['sd']:.3g}", 'In recorded units'), ('IQR outliers', f"{diag['iqr_outlier_pct']:.2f}%", 'Descriptive 1.5×IQR flag; not automatic exclusions')])
show = ['n_total','n_valid','n_missing','missing_pct','mean','sd','cv_pct','min','p01','p05','q1','median','q3','p95','p99','max','skewness','kurtosis_excess','iqr_outlier_n','iqr_outlier_pct','unique_values']
st.dataframe(pd.DataFrame({'diagnostic':show,'value':[diag[k] for k in show]}), use_container_width=True, hide_index=True)
fig = px.histogram(pd.to_numeric(df[phenotype], errors='coerce').dropna(), x=phenotype, nbins=40, marginal='box', title=f'Distribution: {phenotype}')
fig.update_layout(template='plotly_white', height=360)
st.plotly_chart(fig, use_container_width=True)

st.subheader('2. Subgroup structure')
group_candidates = [c for c in df.columns if c != phenotype and (df[c].dtype == 'object' or df[c].nunique(dropna=True) <= 20)]
if group_candidates:
    group = st.selectbox('Grouping variable', group_candidates, index=group_candidates.index('Breed') if 'Breed' in group_candidates else 0)
    prof = group_profile(df, phenotype, group)
    if not prof.empty:
        st.dataframe(prof, use_container_width=True, hide_index=True)
        st.caption('These are descriptive group summaries. Repeated records per animal can inflate apparent precision; use animal-level or mixed-effects inference for formal comparisons.')
else:
    st.caption('No suitable categorical grouping variables detected.')

st.subheader('3. Repeatability and longitudinal consistency')
cols = list(df.columns)
animal_default = 'AnimalID' if 'AnimalID' in cols else cols[0]
animal_col = st.selectbox('Animal identifier', cols, index=cols.index(animal_default))
session_candidates = [c for c in cols if c not in [animal_col, phenotype] and (c.lower() in ['round','session','visit','log_day','file_date'] or df[c].nunique(dropna=True) <= 30)]
session_col = st.selectbox('Session / round variable (optional)', ['None'] + session_candidates, index=(session_candidates.index('Round')+1 if 'Round' in session_candidates else 0))
session_col = None if session_col == 'None' else session_col
if st.button('Calculate repeatability diagnostics', type='primary'):
    try:
        rep, session_summary, paired = repeated_measure_diagnostics(df, animal_col, phenotype, session_col)
        st.session_state['phenotype_validation_repeatability'] = rep
        st.session_state['phenotype_validation_session_summary'] = session_summary
        st.session_state['phenotype_validation_paired'] = paired
    except Exception as exc:
        st.error(str(exc))
rep = st.session_state.get('phenotype_validation_repeatability')
if rep:
    keys = ['n_animals','n_animals_repeated','n_records','ICC_single','ICC_average','mean_repeats','min_repeats','max_repeats']
    st.dataframe(pd.DataFrame({'metric':[k for k in keys if k in rep], 'estimate':[rep[k] for k in keys if k in rep]}), use_container_width=True, hide_index=True)
    if rep.get('icc_error'): st.warning(rep['icc_error'])
    if 'design_note' in rep: st.caption(rep['design_note'])
    if 'paired_session_comparison' in rep: st.json(rep['paired_session_comparison'])
    ss = st.session_state.get('phenotype_validation_session_summary')
    if ss is not None and not ss.empty: st.dataframe(ss, use_container_width=True, hide_index=True)
    pp = st.session_state.get('phenotype_validation_paired')
    if pp is not None and not pp.empty: st.download_button('Download paired animal-session values (CSV)', pp.to_csv(index=False).encode(), 'phenotype_paired_session_values.csv', 'text/csv')
    st.caption('ICC shown here uses a one-way random-effects approximation and may be unsuitable when rounds are fixed, incomplete or structurally different. For publication, select an ICC model matching the design and report confidence intervals.')

st.subheader('4. Association with body weight or another continuous covariate')
cov_candidates = [c for c in nums if c != phenotype]
if cov_candidates:
    cov_default = 'weight' if 'weight' in cov_candidates else cov_candidates[0]
    cov = st.selectbox('Continuous covariate', cov_candidates, index=cov_candidates.index(cov_default))
    aggregate = st.checkbox('Aggregate to one median value per animal before correlation', value=True)
    # Bind cached results to the exact controls used to calculate them. Streamlit
    # reruns the page when a selectbox/checkbox changes, so unkeyed cached results
    # can otherwise be plotted against a different pair of column names.
    association_signature = (phenotype, cov, animal_col if aggregate else None, bool(aggregate))
    if st.button('Estimate association'):
        try:
            res, points = correlate_with_covariate(df, phenotype, cov, animal_col if aggregate else None)
            st.session_state['phenotype_validation_association'] = res
            st.session_state['phenotype_validation_points'] = points
            st.session_state['phenotype_validation_association_signature'] = association_signature
        except Exception as exc:
            st.session_state.pop('phenotype_validation_association', None)
            st.session_state.pop('phenotype_validation_points', None)
            st.session_state.pop('phenotype_validation_association_signature', None)
            st.error(str(exc))

    assoc = st.session_state.get('phenotype_validation_association')
    saved_signature = st.session_state.get('phenotype_validation_association_signature')
    points = st.session_state.get('phenotype_validation_points')
    if assoc and saved_signature == association_signature and isinstance(points, pd.DataFrame):
        # Validate the cached frame before handing it to Plotly. This also gives a
        # useful diagnostic if an older session contains an incomplete result.
        missing_plot_cols = [c for c in (cov, phenotype) if c not in points.columns]
        if missing_plot_cols:
            st.warning('The stored association result does not contain the currently selected columns. Recalculate the association.')
        else:
            plot_points = points[[cov, phenotype]].copy()
            for column in (cov, phenotype):
                plot_points[column] = pd.to_numeric(plot_points[column], errors='coerce')
            plot_points = plot_points.replace([np.inf, -np.inf], np.nan).dropna(subset=[cov, phenotype])
            if len(plot_points) < 2:
                st.warning('At least two complete points are required to draw the association plot.')
            else:
                has_variation = plot_points[cov].nunique() > 1 and plot_points[phenotype].nunique() > 1
                fig2 = px.scatter(
                    plot_points, x=cov, y=phenotype,
                    trendline='ols' if has_variation else None,
                    title=f'{phenotype} vs {cov} (analysis units: {assoc["n_units"]})',
                )
                fig2.update_layout(template='plotly_white', height=360)
                st.plotly_chart(fig2, use_container_width=True)
            st.json(assoc)
            st.caption('Correlation is descriptive. Animal-level aggregation reduces pseudoreplication but does not adjust for breed, sex, round, diet, age or other confounding.')
    elif assoc:
        st.info('The phenotype, covariate or aggregation setting has changed. Select “Estimate association” to calculate results for the current settings.')

st.subheader('5. Candidate phenotype evidence checklist')
items = [
    'Construct and biological rationale defined before examining associations',
    'Formula, source variables, units and dimensional consistency documented',
    'Measurement protocol, instrument calibration and QC criteria documented',
    'Missingness, outliers, floor/ceiling effects and distribution reviewed',
    'Repeatability model and confidence interval appropriate to the sampling design',
    'Between-round agreement and absolute change assessed, not correlation alone',
    'Breed, sex, body weight, diet and other confounders considered',
    'Predictive value assessed with animal-grouped validation and leakage controls',
    'External or temporal validation performed in an independent sample',
]
checks = {item: st.checkbox(item, key='phval_'+str(i)) for i,item in enumerate(items)}
completed = sum(checks.values())
st.progress(completed/len(items), text=f'{completed} of {len(items)} review criteria marked complete')
report = {'phenotype': phenotype, 'distribution_diagnostics': diag, 'repeatability_diagnostics': rep or {}, 'association_diagnostics': st.session_state.get('phenotype_validation_association', {}), 'review_checklist': checks, 'interpretation': 'Exploratory evidence only; no automated biological validity certification.'}
st.download_button('Export phenotype validation report (JSON)', pd.Series(report).to_json(indent=2).encode(), 'phenotype_validation_report.json', 'application/json')
st.warning('Do not label an animal a high/low methane emitter or convert instrument signals to methane mass (e.g., g/day) without an appropriate calibrated measurement model. A strong ICC alone does not establish validity.')
