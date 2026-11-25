import pandas as pd
from platform_core.analysis_context import resolve_analysis_context


def test_analysis_context_fingerprints_dataset_and_resolves_scopes(tmp_path, monkeypatch):
    monkeypatch.setenv('ANALYSIS_REGISTRY_PATH', str(tmp_path / 'settings.sqlite3'))
    monkeypatch.delenv('METHANE_METADATA_DB', raising=False)
    state = {
        'user_id': 'user-1', 'active_project_id': 'project-1',
        'active_dataset_id': 'dataset-1', 'data_name': 'study.csv', 'species': 'sheep'
    }
    df = pd.DataFrame({'AnimalID': ['A1', 'A2'], 'CH4': [12.0, 13.0]})
    context = resolve_analysis_context(df, state)
    assert context['project_id'] == 'project-1'
    assert context['dataset_id'] == 'dataset-1'
    assert context['species'] == 'sheep'
    assert len(context['dataset_fingerprint']) == 64
    assert state['active_analysis_context']['dataset_fingerprint'] == context['dataset_fingerprint']
    assert 'settings' in context and 'settings_errors' in context
