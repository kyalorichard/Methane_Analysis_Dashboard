import streamlit as st, pandas as pd
from analysis_engine.ui import header, get_data, get_roles
from platform_core.species import PROFILES, infer_species_roles, get_profile
from platform_core.data_governance import validate_species_dataset
from analysis_engine.ui import render_sidebar_navigation
render_sidebar_navigation()

header('Species & protocol configuration','Review species-specific variable mapping and measurement metadata before analysis.')
df=get_data();species=st.session_state.get('species','sheep');profile=get_profile(species)
st.subheader(f'{profile.label} adapter')
st.info(profile.note)
roles=infer_species_roles(df.columns,species)
role_labels={'animal_id':'Animal identifier','breed':'Breed / group','sex':'Sex','weight':'Body weight','round':'Measurement round / session','date':'Measurement date','methane':'Methane signal / phenotype','recording_duration':'Recording duration'}
for role,label in role_labels.items():
 opts=['—']+list(df.columns);current=roles.get(role);ix=opts.index(current) if current in opts else 0
 roles[role]=st.selectbox(label,opts,index=ix,key='species_role_'+role)
st.session_state['roles']=roles
st.subheader('Protocol metadata')
a,b=st.columns(2)
with a:
 instrument=st.text_input('Instrument / measurement system',value=st.session_state.get('protocol_instrument',''))
 method=st.selectbox('Measurement method',['Not specified','Respiration chamber','GreenFeed','Laser methane detector','Portable accumulation chamber','Breath sampling','Other'])
 units=st.text_input('Methane variable units',value=st.session_state.get('protocol_units',''))
with b:
 calibration=st.selectbox('Calibration status',['Not documented','Manufacturer calibration only','Study-specific validated calibration','Not applicable / presence-only signal'])
 protocol=st.text_input('Protocol / SOP reference',value=st.session_state.get('protocol_ref',''))
 min_duration=st.number_input('Minimum valid recording duration (seconds)',min_value=0.0,value=float(st.session_state.get('protocol_min_duration',0.0)),step=10.0)
if st.button('Save protocol metadata',type='primary'):
 st.session_state.update({'protocol_instrument':instrument,'protocol_method':method,'protocol_units':units,'protocol_calibration':calibration,'protocol_ref':protocol,'protocol_min_duration':min_duration})
 st.success('Protocol metadata saved for this session. Persistent project storage requires the connected database service.')
st.subheader('Adapter validation')
issues=validate_species_dataset(df,species)
if issues:
 for issue in issues: st.warning(issue)
else: st.success('Core identifiers and candidate methane signal were detected. Complete protocol metadata review before inferential analysis.')
st.dataframe(pd.DataFrame([{'role':k,'mapped_variable':v} for k,v in roles.items()]),use_container_width=True)
st.warning('Do not assume identical phenotype definitions across species or instruments. Record units, calibration, measurement method, sampling duration and protocol version for every dataset.')
