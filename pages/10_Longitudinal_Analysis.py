import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from analysis_engine.ui import *
from analysis_engine.ui import render_sidebar_navigation
from analysis_engine.longitudinal import (
    paired_round_changes, fit_longitudinal_mixed_model,
    longitudinal_prediction_frame, longitudinal_residual_diagnostics,
    compare_longitudinal_models,
)

render_sidebar_navigation()
header('Longitudinal analysis', 'Model animal-level change over time, retain unbalanced records, and inspect uncertainty and assumptions.')
df = get_data()
r = get_roles(df)
animal = r.get('animal_id')
roundc = r.get('round')
datec = r.get('date')
nums = numeric_cols(df)
out = choose_col(df, 'Phenotype outcome', r.get('methane'), nums)

if roundc:
    sm = grouped_summary(df, roundc, out)
    st.subheader('Phenotype by monitoring round')
    st.dataframe(sm, use_container_width=True)
    st.plotly_chart(px.box(df, x=roundc, y=out, points='outliers', title=f'{out} by round'), use_container_width=True)
if animal and roundc:
    d = df[[animal, roundc, out]].copy()
    d[out] = pd.to_numeric(d[out], errors='coerce')
    p = d.pivot_table(index=animal, columns=roundc, values=out, aggfunc='median')
    if p.shape[1] >= 2:
        st.subheader('Paired animal-level changes')
        cols = list(p.columns)
        a, b = st.columns(2)
        a.selectbox('Baseline round', cols, key='base_round')
        base = st.session_state['base_round']
        comparison_options = [value for value in cols if value != base]
        if st.session_state.get('comp_round') not in comparison_options:
            st.session_state['comp_round'] = comparison_options[0]
        b.selectbox('Comparison round', comparison_options, key='comp_round')
        try:
            paired = paired_round_changes(p, base, st.session_state['comp_round'])
        except ValueError as exc:
            st.warning(str(exc))
        else:
            if paired.empty:
                st.info('No animals have non-missing measurements in both selected rounds.')
            else:
                metric_row([('PAIRED ANIMALS', f'{len(paired):,}', 'Complete pair'),
                            ('MEDIAN CHANGE', f'{paired.change.median():.3f}', 'Comparison minus baseline'),
                            ('MEAN CHANGE', f'{paired.change.mean():.3f}', 'Comparison minus baseline')])
                st.plotly_chart(px.histogram(paired, x='change', nbins=30, title='Distribution of within-animal change'), use_container_width=True)

st.divider()
st.subheader('Mixed-effects trajectory model')
st.caption('The model uses all eligible repeated records without requiring a balanced panel. Missing rows are excluded transparently; irregular measurement times are retained as observed, not interpolated.')
allcols = list(df.columns)
date_candidates = [c for c in allcols if c == datec or pd.api.types.is_datetime64_any_dtype(df[c])]
time_options = list(dict.fromkeys([c for c in nums if c != out] + date_candidates))
subject_default = animal if animal in allcols else (allcols[0] if allcols else None)
time_default = datec if datec in allcols else (next((c for c in nums if c != out), None))
if len(allcols) >= 2 and time_options:
    c1, c2, c3 = st.columns(3)
    subject = c1.selectbox('Subject / animal ID', allcols, index=allcols.index(subject_default) if subject_default else 0, key='long_subject')
    time_col = c2.selectbox('Time / occasion variable', time_options, index=time_options.index(time_default) if time_default in time_options else 0, key='long_time')
    time_kind = c3.radio('Time encoding', ['numeric', 'date'], horizontal=True, index=1 if time_col == datec else 0, key='long_time_kind')
    treatment_options = [None] + [c for c in allcols if c not in {out, subject, time_col}]
    treatment = st.selectbox('Treatment / group (optional)', treatment_options, format_func=lambda x: 'None' if x is None else x, key='long_treatment')
    covar_options = [c for c in allcols if c not in {out, subject, time_col, treatment}]
    covars = st.multiselect('Additional fixed-effect covariates', covar_options, key='long_covars')
    c4, c5, c6 = st.columns(3)
    time_form = c4.selectbox('Fixed time trend', ['linear', 'cubic spline'], key='long_time_form')
    spline_df = c5.slider('Spline degrees of freedom', 3, 6, 4, disabled=time_form == 'linear', key='long_spline_df')
    random_slope = c6.checkbox('Animal-specific linear time slope', True, key='long_random_slope')
    run = st.button('Fit longitudinal model', type='primary', key='fit_longitudinal_model')
    config = {'outcome': out, 'subject': subject, 'time': time_col, 'time_kind': time_kind,
              'treatment': treatment, 'covars': covars, 'time_form': time_form,
              'spline_df': spline_df, 'random_slope': random_slope}
    config_key = json.dumps(config, sort_keys=True, default=str)
    if run:
        try:
            model, used, audit = fit_longitudinal_mixed_model(
                df, out, time_col, subject, covars, treatment, time_kind,
                'spline' if time_form == 'cubic spline' else 'linear', spline_df,
                random_slope, reml=False)
            predictions = longitudinal_prediction_frame(model, used, treatment_col=treatment)
            diagnostics, diag_summary = longitudinal_residual_diagnostics(model, used)
            st.session_state['longitudinal_model_bundle'] = {
                'config_key': config_key, 'audit': audit, 'summary': model.summary().as_text(),
                'predictions': predictions, 'diagnostics': diagnostics,
                'diag_summary': diag_summary, 'aic': float(model.aic), 'bic': float(model.bic),
                'model': model, 'used': used, 'config': config,
            }
        except Exception as exc:
            st.error(f'{type(exc).__name__}: {exc}')
    bundle = st.session_state.get('longitudinal_model_bundle')
    if bundle and bundle.get('config_key') == config_key:
        audit = bundle['audit']
        st.markdown('**Model fit summary**')
        metric_row([('ANIMALS', f"{audit['subjects']:,}", 'Independent subject clusters'),
                    ('RECORDS USED', f"{audit['complete_records']:,}", 'Complete observations'),
                    ('ROWS EXCLUDED', f"{audit['dropped_records'] + audit['excluded_nonrepeated_records']:,}", 'Missing / invalid values or subjects without repeated time points'),
                    ('AIC', f"{bundle['aic']:.1f}", 'Maximum-likelihood fit')])
        if audit['converged']:
            st.success('Optimizer reported convergence. This is necessary but not sufficient evidence of an adequate model.')
        else:
            st.warning('The model did not report convergence. Treat estimates as unreliable until model structure, scaling and data support are reviewed.')
        st.caption(f"Fixed time form: {audit['time_form']} · Random structure: {audit['random_effects']} · Unequal visit counts: {audit['subjects_with_unequal_visit_counts']} · Irregular spacing: {audit['subjects_with_irregular_spacing']}")
        st.code(bundle['summary'])
        st.subheader('Population-level predicted trajectory')
        pred = bundle['predictions']
        if treatment:
            fig = px.line(pred, x='time', y='predicted', color=treatment, title='Predicted trajectories with 95% confidence intervals')
            for level, part in pred.groupby(treatment):
                fig.add_trace(go.Scatter(x=part['time'], y=part['ci_upper'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                fig.add_trace(go.Scatter(x=part['time'], y=part['ci_lower'], mode='lines', line=dict(width=0), fill='tonexty', showlegend=False, hoverinfo='skip'))
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pred['time'], y=pred['predicted'], mode='lines', name='Predicted mean'))
            fig.add_trace(go.Scatter(x=pred['time'], y=pred['ci_upper'], mode='lines', line=dict(width=0), showlegend=False))
            fig.add_trace(go.Scatter(x=pred['time'], y=pred['ci_lower'], mode='lines', line=dict(width=0), fill='tonexty', showlegend=False))
            fig.update_layout(title='Population-level predicted trajectory with 95% confidence interval', xaxis_title='Elapsed time / occasion', yaxis_title=out)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Confidence intervals describe uncertainty in the population-average fixed-effect prediction, not prediction intervals for individual animals.')
        st.subheader('Residual diagnostics')
        diag = bundle['diagnostics']
        d1, d2 = st.columns(2)
        d1.plotly_chart(px.scatter(diag, x='fitted', y='standardized_residual', color=subject if subject in diag else None, title='Standardized residuals vs fitted'), use_container_width=True)
        d2.plotly_chart(px.histogram(diag, x='standardized_residual', nbins=30, title='Standardized residual distribution'), use_container_width=True)
        st.json(bundle['diag_summary'])
        st.dataframe(diag.head(500), use_container_width=True)
        st.download_button('Download model diagnostics (CSV)', diag.to_csv(index=False), 'longitudinal_model_diagnostics.csv', 'text/csv')
        st.download_button('Download predicted trajectory (CSV)', pred.to_csv(index=False), 'longitudinal_predicted_trajectory.csv', 'text/csv')
        st.subheader('Random-intercept vs random-slope sensitivity')
        if random_slope:
            if st.button('Fit random-intercept comparator', key='long_fit_intercept_comparator'):
                try:
                    base_model, _, _ = fit_longitudinal_mixed_model(
                        df, out, time_col, subject, covars, treatment, time_kind,
                        'spline' if time_form == 'cubic spline' else 'linear', spline_df,
                        False, reml=False)
                    comp_table, comp_stats = compare_longitudinal_models(base_model, bundle['model'], same_data=True, nested=False)
                    st.session_state['longitudinal_model_comparison'] = {'config_key': config_key, 'table': comp_table, 'stats': comp_stats}
                except Exception as exc:
                    st.error(f'Comparator fit failed: {exc}')
            comparison = st.session_state.get('longitudinal_model_comparison')
            if comparison and comparison.get('config_key') == config_key:
                st.dataframe(comparison['table'], use_container_width=True)
                st.info('Compare AIC/BIC only. The random-intercept model is nested in the random-slope model, but testing a variance component at the zero boundary does not generally follow an ordinary chi-square likelihood-ratio reference distribution.')
        st.download_button('Download model audit (JSON)', json.dumps(audit, indent=2, default=str), 'longitudinal_model_audit.json', 'application/json')
    elif bundle:
        st.info('Model controls have changed. Fit the model again to replace the previous results; stale results are not displayed.')
else:
    st.info('A numeric or date time variable and a subject identifier are required for longitudinal mixed-effects modelling. Map these variables in Data Preparation, or load a dataset with repeated time observations.')

if datec:
    t = df[[datec, out]].copy()
    t[datec] = pd.to_datetime(t[datec], errors='coerce')
    t[out] = pd.to_numeric(t[out], errors='coerce')
    t = t.dropna().set_index(datec).sort_index()
    if len(t):
        st.subheader('Descriptive monthly aggregate')
        st.plotly_chart(px.line(t.resample('ME')[out].mean().reset_index(), x=datec, y=out, title='Monthly aggregate mean (descriptive)'), use_container_width=True)
st.warning('Aggregate time trends are descriptive. Mixed-effects estimates remain conditional on the specified mean, covariance and missing-data assumptions. Forecasting requires adequate temporal density and out-of-time validation.')
