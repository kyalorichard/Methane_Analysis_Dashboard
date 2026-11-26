from pathlib import Path


def test_project_workspace_exposes_open_create_and_import_lifecycle():
    source = Path("pages/00_Project_Workspace.py").read_text(encoding="utf-8")
    assert '"Open existing project"' in source
    assert '"Create new project"' in source
    assert '"Import project archive"' in source
    assert 'st.button("Open project"' in source


def test_open_project_restores_dataset_and_saved_configuration():
    source = Path("pages/00_Project_Workspace.py").read_text(encoding="utf-8")
    assert "load_dataset(principal.tenant_id, open_project[\"id\"]" in source
    assert "get_dataset_configuration" in source
    assert 'st.session_state["measurement_protocol"] = restored_protocol' in source
    assert 'st.session_state["roles"] = saved_config.get("variable_mapping")' in source


def test_project_checkpoint_and_portable_export_remain_available():
    source = Path("pages/00_Project_Workspace.py").read_text(encoding="utf-8")
    assert 'st.button("Save project checkpoint"' in source
    assert "build_project_archive" in source
    assert 'st.download_button("Download project ZIP"' in source
