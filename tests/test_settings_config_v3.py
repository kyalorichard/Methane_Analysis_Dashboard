import json
from analysis_engine.settings_config import defaults, migrate_settings, validate_settings, config_fingerprint


def test_v3_defaults_cover_all_configuration_domains():
    cfg = defaults()
    assert cfg['schema_version'] == 3
    assert {'study','preprocessing','statistics','comparison','conventional','models','clustering','repeatability','forecasting','evaluation','reporting'} <= set(cfg)
    errors, _ = validate_settings(cfg)
    assert errors == []


def test_legacy_settings_migrate_without_losing_supported_values():
    legacy = {'schema_version': 2, 'comparison': {'random_state': 123}, 'models': {'SVR': {'C': 3.0}}}
    migrated = migrate_settings(legacy)
    assert migrated['schema_version'] == 3
    assert migrated['comparison']['random_state'] == 123
    assert migrated['models']['SVR']['C'] == 3.0
    assert 'forecasting' in migrated and 'repeatability' in migrated


def test_validation_flags_invalid_cluster_range_and_test_size():
    cfg = defaults()
    cfg['clustering']['min_clusters'] = 8
    cfg['clustering']['max_clusters'] = 3
    cfg['comparison']['test_size'] = 1.0
    errors, _ = validate_settings(cfg)
    assert any('cluster' in e.lower() for e in errors)
    assert any('test size' in e.lower() for e in errors)


def test_configuration_fingerprint_is_stable():
    cfg = defaults()
    assert config_fingerprint(cfg) == config_fingerprint(json.loads(json.dumps(cfg)))
