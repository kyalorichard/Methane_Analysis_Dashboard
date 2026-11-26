from pathlib import Path


def test_analysis_history_and_comparison_are_scoped_to_principal_and_project():
    history = Path("pages/26_Analysis_Run_History.py").read_text(encoding="utf-8")
    comparison = Path("pages/29_Analysis_Comparison.py").read_text(encoding="utf-8")
    assert "tenant_id=principal.tenant_id" in history
    assert "project_id=st.session_state.get(\"active_project_id\")" in history
    assert "user_subject=principal.subject" in history
    assert "tenant_id=principal.tenant_id" in comparison
    assert "user_subject=principal.subject" in comparison


def test_data_preparation_can_persist_immutable_project_dataset_version():
    source = Path("pages/24_Data_Preparation_Studio.py").read_text(encoding="utf-8")
    assert 'st.button("Save prepared dataset version"' in source
    assert "store.save_dataset(" in source
    assert "source_dataset_id" in source
    assert 'st.session_state["active_dataset_id"] = saved["id"]' in source


def test_shared_header_shows_project_dataset_and_persistence_state():
    source = Path("analysis_engine/ui.py").read_text(encoding="utf-8")
    assert "def render_workspace_context()" in source
    assert "Saved project dataset" in source
    assert "Temporary session dataset" in source
    assert "render_workspace_context()" in source


def test_cloud_settings_have_tenant_scoped_postgres_schema_and_migration():
    schema = Path("database/schema.sql").read_text(encoding="utf-8")
    migration = Path("database/migrations/007_project_settings.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS project_settings" in schema
    assert "CREATE TABLE IF NOT EXISTS project_settings_history" in schema
    assert "ALTER TABLE project_settings ENABLE ROW LEVEL SECURITY" in schema
    assert "CREATE POLICY tenant_project_settings" in migration
    assert "CREATE POLICY tenant_project_settings_history" in migration


def test_cloud_settings_reject_unscoped_project_names():
    from analysis_engine.experiment_registry import _cloud_settings_context
    import pytest
    with pytest.raises(ValueError, match="authenticated tenant"):
        _cloud_settings_context("user-1", "default-project", None)
    with pytest.raises(ValueError, match="saved project ID"):
        _cloud_settings_context("user-1", "Study name", "tenant-id")


def test_settings_runtime_uses_defaults_without_cloud_project(monkeypatch):
    from analysis_engine.settings_config import load_active_settings, defaults
    monkeypatch.setattr("platform_core.storage.backend_name", lambda: "cloud")
    state = {"principal": {"subject": "user-1", "tenant_id": "tenant-1"}}
    result = load_active_settings(state)
    assert result == defaults()
    assert state["analysis_settings_validation"]["warnings"]


def test_model_settings_page_routes_settings_through_tenant_aware_registry():
    source = Path("pages/36_Analysis_Model_Settings.py").read_text(encoding="utf-8")
    assert "tenant_id=tenant_id" in source
    assert "disabled=cloud_backend" in source
    assert "PostgreSQL under the active tenant and project" in source
