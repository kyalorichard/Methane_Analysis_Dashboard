import streamlit as st
import pandas as pd
from analysis_engine.ui import header, render_sidebar_navigation
from platform_core.auth import require_principal
from analysis_engine.study_harmonisation import audit_protocol_comparability, dersimonian_laird, harmonise_study_frame

st.set_page_config(page_title='Multi-study harmonisation | Methane Phenotype Analytics', page_icon='🧬', layout='wide')
require_principal()
render_sidebar_navigation()
header('Multi-study harmonisation & meta-analysis', 'Explicit phenotype mapping, measurement-protocol comparability and random-effects synthesis across independent studies.')
st.warning('Do not pool raw methane values across species or studies solely because column names match. Confirm phenotype definition, units, instrument, calibration, sampling design and biological estimand first.')

with st.expander('1. Harmonise one study dataset', expanded=True):
    file=st.file_uploader('Study dataset (CSV)',type=['csv'],key='harm_csv')
    if file:
        df=pd.read_csv(file)
        st.caption(f'{len(df):,} rows · {len(df.columns):,} columns')
        st.dataframe(df.head(10),use_container_width=True)
        c1,c2,c3=st.columns(3)
        with c1:
            study=st.text_input('Study identifier')
            species=st.selectbox('Species',['sheep','goat','cattle','buffalo','camel','other'])
            phenotype=st.text_input('Phenotype name',placeholder='e.g. methane production')
        with c2:
            source=st.selectbox('Source methane variable',list(df.columns))
            unit=st.text_input('Canonical output unit',placeholder='e.g. g CH4/day')
            factor=st.number_input('Explicit conversion multiplier',value=1.0,format='%.8f')
        with c3:
            definition=st.text_input('Phenotype definition')
            method=st.text_input('Measurement method')
            instrument=st.text_input('Measurement instrument')
            calibration=st.text_input('Calibration reference / standard')
        animal=st.selectbox('Animal identifier (optional)', ['(none)']+list(df.columns))
        weight=st.selectbox('Body-weight variable (optional)', ['(none)']+list(df.columns))
        if st.button('Create harmonised study extract',type='primary'):
            try:
                mapping={'methane_value':source}
                if animal!='(none)': mapping['animal_id']=animal
                if weight!='(none)': mapping['body_weight_kg']=weight
                result=harmonise_study_frame(df,study_id=study,species=species,column_mapping=mapping,unit=unit,phenotype=phenotype,phenotype_definition=definition,measurement_method=method,instrument=instrument,calibration_reference=calibration,conversion_factor=factor)
                st.success('Harmonised extract created. Review metadata and units before combining with other studies.')
                st.dataframe(result.head(20),use_container_width=True)
                st.download_button('Download harmonised CSV',result.to_csv(index=False).encode(),file_name=f'{study or "study"}_harmonised.csv',mime='text/csv')
            except Exception as exc: st.error(str(exc))

st.divider()
with st.expander('2. Audit protocol comparability'):
    pfile=st.file_uploader('Protocol metadata table (CSV)',type=['csv'],key='protocol_csv')
    st.caption('Required columns: species, phenotype, phenotype_definition, unit, measurement_method, instrument, calibration_reference. One row per study.')
    if pfile:
        protocols=pd.read_csv(pfile)
        audit=audit_protocol_comparability(protocols)
        if audit['comparable']: st.success(audit['message'])
        else: st.warning(audit['message'])
        st.json(audit)
        st.dataframe(protocols,use_container_width=True)

st.divider()
with st.expander('3. Random-effects meta-analysis',expanded=True):
    mfile=st.file_uploader('Study effect estimates CSV',type=['csv'],key='meta_csv')
    st.caption('Provide one independent effect estimate and its standard error per study. All estimates must represent the same effect measure and estimand.')
    if mfile:
        meta=pd.read_csv(mfile)
        a,b=st.columns(2)
        effect_col=a.selectbox('Effect estimate column',list(meta.columns))
        se_col=b.selectbox('Standard error column',[c for c in meta.columns if c!=effect_col])
        if st.button('Run DerSimonian–Laird synthesis'):
            try:
                result=dersimonian_laird(meta[effect_col],meta[se_col])
                st.metric('Pooled random-effects estimate',f"{result['pooled_effect']:.4f}")
                x,y,z=st.columns(3)
                x.metric('95% confidence interval',f"{result['ci_low']:.4f} to {result['ci_high']:.4f}")
                y.metric('I²',f"{result['i_squared_percent']:.1f}%")
                z.metric('Between-study variance (τ²)',f"{result['tau_squared']:.5f}")
                st.json(result)
                st.dataframe(meta,use_container_width=True)
            except Exception as exc: st.error(str(exc))

st.info('Methodological limits: this release implements DerSimonian–Laird random-effects pooling of supplied study effects. It does not automatically calculate Hedges g from raw animal data, fit multilevel/multivariate meta-analysis, adjust for study-level moderators, or establish cross-species phenotype equivalence. With few studies, τ² and I² are uncertain; inspect forest plots and sensitivity analyses before interpretation.')
