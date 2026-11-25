import copy
from analysis_engine.settings_config import defaults, migrate_settings, validate_settings, config_fingerprint

def test_settings_migration_fills_missing_sections_and_preserves_values():
    cfg = migrate_settings({"statistics": {"alpha": 0.01}, "forecasting": {"horizon": 8}})
    assert cfg["schema_version"] == 3
    assert cfg["statistics"]["alpha"] == 0.01
    assert cfg["forecasting"]["horizon"] == 8
    assert "repeatability" in cfg and "evaluation" in cfg

def test_settings_validation_detects_invalid_forecast_and_reporting_values():
    cfg = defaults()
    cfg["forecasting"]["test_fraction"] = 1.0
    cfg["reporting"]["decimals"] = 11
    errors, _ = validate_settings(cfg)
    assert any("Forecast holdout" in x for x in errors)
    assert any("decimal places" in x for x in errors)

def test_configuration_fingerprint_is_order_independent():
    cfg = defaults()
    altered = copy.deepcopy(cfg)
    altered["statistics"] = dict(reversed(list(altered["statistics"].items())))
    assert config_fingerprint(cfg) == config_fingerprint(altered)


def test_active_settings_scope_uses_authenticated_principal_and_project(monkeypatch, tmp_path):
    from analysis_engine import settings_config
    from analysis_engine import experiment_registry
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "settings.sqlite3"))
    state = {"principal": {"subject": "user-123"}, "active_project_id": "project-456", "species": "sheep"}
    cfg = settings_config.load_active_settings(state)
    assert state["user_id"] == "user-123"
    assert state["analysis_settings_scope_key"] == "user-123|project-456|sheep"
    assert cfg["schema_version"] == 3
