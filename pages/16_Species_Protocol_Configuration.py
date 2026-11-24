"""Dataset-scoped species, variable mapping and measurement protocol configuration."""
import os
import pandas as pd
import streamlit as st

from analysis_engine.ui import header, render_sidebar_navigation
from platform_core.auth import require_principal
from platform_core.database import configured
from platform_core import local_workspace
from platform_core import workspace as cloud_workspace
from platform_core.species import PROFILES, infer_species_roles, get_profile
from platform_core.data_governance import validate_species_dataset

render_sidebar_navigation()
header(
    'Species & protocol configuration',
    'Configure species, variable roles and measurement metadata separately for each stored dataset.'
)
principal = require_principal()
backend = os.getenv('PROJECT_STORAGE_BACKEND', 'cloud' if (configured() and os.getenv('S3_BUCKET')) else 'local').lower()
if backend not in {'local', 'cloud'}:
    st.error("PROJECT_STORAGE_BACKEND must be 'local' or 'cloud'.")
    st.stop()
if backend == 'cloud' and not configured():
    st.error('Cloud project storage is selected but DATABASE_URL is not configured.')
    st.stop()
store = local_workspace if backend == 'local' else cloud_workspace

try:
    projects = store.list_projects(principal.tenant_id, principal.subject)
except Exception as exc:
    st.error(f'Unable to load projects: {exc}')
    st.stop()
if not projects:
    st.info('Create a project and save at least one dataset in Projects & datasets before configuring its species and protocol.')
    st.stop()

project_labels = {f"{p['name']} · {p['species'].title()} · {p['id'][:8]}": p for p in projects}
current_project_id = st.session_state.get('active_project_id')
project_keys = list(project_labels)
default_project = next((k for k, v in project_labels.items() if v['id'] == current_project_id), project_keys[0])
selected_project_label = st.selectbox('Project', project_keys, index=project_keys.index(default_project), key='species_config_project')
project = project_labels[selected_project_label]
project_id = project['id']

try:
    datasets = store.list_datasets(principal.tenant_id, project_id, principal.subject)
except Exception as exc:
    st.error(f'Unable to retrieve datasets for this project: {exc}')
    st.stop()
if not datasets:
    st.info('This project does not yet contain a stored dataset. Upload one in Projects & datasets → Datasets & protocols.')
    st.stop()

dataset_labels = {f"{d['name']} · {int(d.get('row_count') or 0):,} rows · {d['id'][:8]}": d for d in datasets}
active_id = st.session_state.get('active_dataset_id')
dataset_keys = list(dataset_labels)
default_dataset = next((k for k, v in dataset_labels.items() if v['id'] == active_id), dataset_keys[0])
selected_dataset_label = st.selectbox('Dataset', dataset_keys, index=dataset_keys.index(default_dataset), key='species_config_dataset')
dataset = dataset_labels[selected_dataset_label]
dataset_id = dataset['id']

try:
    df, dataset_name, stored_species = store.load_dataset(principal.tenant_id, project_id, dataset_id, principal.subject)
    saved = store.get_dataset_configuration(principal.tenant_id, principal.subject, project_id, dataset_id)
except Exception as exc:
    st.error(f'Unable to load the selected dataset/configuration: {exc}')
    st.stop()

st.session_state['active_project_id'] = project_id
st.session_state['active_dataset_id'] = dataset_id
st.session_state['analysis_project_scope'] = project['name']
st.caption(f"Storage: {'Local SQLite + filesystem' if backend == 'local' else 'PostgreSQL + S3'} · Dataset: {dataset_name} · {len(df):,} rows × {df.shape[1]:,} variables")

species_keys = list(PROFILES.keys())
saved_species = saved.get('species') or stored_species or project['species']
species_index = species_keys.index(saved_species) if saved_species in species_keys else species_keys.index(project['species']) if project['species'] in species_keys else 0
species = st.selectbox('Livestock species for this dataset', species_keys, format_func=lambda x: PROFILES[x].label, index=species_index, key=f'cfg_species_{dataset_id}')
profile = get_profile(species)
st.info(profile.note)

st.subheader('1. Variable mapping')
st.caption('Automatic mapping is based on recognised column aliases. Confirm each selection against the data dictionary and study protocol.')
inferred = infer_species_roles(df.columns, species)
saved_roles = saved.get('variable_mapping') or {}
role_labels = {
    'animal_id': 'Animal identifier', 'breed': 'Breed / group', 'sex': 'Sex',
    'weight': 'Body weight', 'round': 'Measurement round / session',
    'date': 'Measurement date', 'methane': 'Methane signal / phenotype',
    'recording_duration': 'Recording duration'
}
roles = {}
left, right = st.columns(2)
for i, (role, label) in enumerate(role_labels.items()):
    options = ['—'] + list(df.columns)
    candidate = saved_roles.get(role) or inferred.get(role)
    idx = options.index(candidate) if candidate in options else 0
    with (left if i % 2 == 0 else right):
        selected = st.selectbox(label, options, index=idx, key=f'cfg_{dataset_id}_{role}')
    roles[role] = None if selected == '—' else selected

st.subheader('2. Measurement protocol metadata')
st.caption('These values describe this dataset only. Different datasets in the same project can use different protocols.')
protocol = saved.get('measurement_protocol') or {}
methods = ['Not specified', 'Respiration chamber', 'GreenFeed', 'Laser methane detector', 'Portable accumulation chamber', 'Breath sampling', 'Other']
calibrations = ['Not documented', 'Manufacturer calibration only', 'Study-specific validated calibration', 'Not applicable / presence-only signal']
p1, p2 = st.columns(2)
with p1:
    instrument = st.text_input('Instrument / measurement system', value=str(protocol.get('instrument', '')), key=f'cfg_{dataset_id}_instrument')
    method_default = protocol.get('method', 'Not specified')
    method = st.selectbox('Measurement method', methods, index=methods.index(method_default) if method_default in methods else 0, key=f'cfg_{dataset_id}_method')
    units = st.text_input('Methane variable units', value=str(protocol.get('units', '')), key=f'cfg_{dataset_id}_units', help='Examples: ppm, ppm·s, g/day. Use physical flux units only when supported by validated calibration.')
with p2:
    calibration_default = protocol.get('calibration_status', 'Not documented')
    calibration = st.selectbox('Calibration status', calibrations, index=calibrations.index(calibration_default) if calibration_default in calibrations else 0, key=f'cfg_{dataset_id}_calibration')
    protocol_ref = st.text_input('Protocol / SOP reference or version', value=str(protocol.get('protocol_reference', '')), key=f'cfg_{dataset_id}_protocol_ref')
    min_duration = st.number_input('Minimum valid recording duration (seconds)', min_value=0.0, value=float(protocol.get('minimum_recording_duration_seconds', 0.0) or 0.0), step=10.0, key=f'cfg_{dataset_id}_min_duration')

st.subheader('3. Configuration validation')
issues = validate_species_dataset(df, species)
if roles.get('animal_id') is None:
    issues.append('Animal identifier is not mapped. Repeated-measures analysis and animal-grouped validation will be limited.')
if roles.get('methane') is None:
    issues.append('Methane signal / phenotype variable is not mapped.')
if roles.get('recording_duration') is None:
    issues.append('Recording duration is not mapped; duration-based QC and sensitivity analysis may be unavailable.')
if not units.strip():
    issues.append('Methane variable units are not documented.')
if method == 'Not specified':
    issues.append('Measurement method has not been specified.')
if calibration == 'Not documented':
    issues.append('Calibration status has not been documented.')
if issues:
    for issue in dict.fromkeys(issues):
        st.warning(issue)
else:
    st.success('Required variable mappings and core protocol metadata have been reviewed. This is a configuration check, not scientific validation of the measurement.')

st.subheader('4. Save dataset configuration')
st.write('Saving writes the species, variable mapping and measurement protocol to the selected dataset record in the project workspace. The configuration is restored when this dataset is selected again.')
if st.button('Save configuration for this dataset', type='primary', key=f'save_dataset_config_{dataset_id}'):
    new_protocol = {
        'instrument': instrument.strip(), 'method': method, 'units': units.strip(),
        'calibration_status': calibration, 'protocol_reference': protocol_ref.strip(),
        'minimum_recording_duration_seconds': float(min_duration)
    }
    try:
        store.save_dataset_configuration(principal.tenant_id, principal.subject, project_id, dataset_id, species, roles, new_protocol)
        st.session_state['species'] = species
        st.session_state['roles'] = roles
        st.session_state['measurement_protocol'] = new_protocol
        st.session_state['protocol_instrument'] = instrument.strip()
        st.session_state['protocol_method'] = method
        st.session_state['protocol_units'] = units.strip()
        st.session_state['protocol_calibration'] = calibration
        st.session_state['protocol_ref'] = protocol_ref.strip()
        st.session_state['protocol_min_duration'] = float(min_duration)
        st.success('Dataset-level species and measurement configuration saved successfully.')
    except Exception as exc:
        st.error(f'Configuration could not be saved: {exc}')

with st.expander('Current saved configuration'):
    st.json({
        'dataset_id': dataset_id,
        'dataset_name': dataset_name,
        'species': saved.get('species') or stored_species,
        'variable_mapping': saved.get('variable_mapping') or {},
        'measurement_protocol': saved.get('measurement_protocol') or {},
        'configuration_version': saved.get('configuration_version', 0),
        'last_updated': saved.get('updated_at')
    })

st.warning('Scientific safeguards: keep methane production, yield, intensity and sensor-derived signal phenotypes distinct. Concentration or AUC is not methane mass flux without validated calibration. QC warnings require review; they do not automatically justify excluding records.')
