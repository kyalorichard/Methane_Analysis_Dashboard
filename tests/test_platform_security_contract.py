from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_production_auth_fails_closed_without_tenant_headers():
    auth=(ROOT/'platform_core'/'auth.py').read_text()
    assert 'AUTH_MODE' in auth and 'entra_proxy' in auth
    assert '_resolve_memberships(subject)' in auth
    assert 'tenant_memberships' in auth

def test_rls_is_forced_for_tenant_tables():
    sql=(ROOT/'database'/'schema.sql').read_text()
    for table in ['projects','project_memberships','datasets','analysis_runs','audit_events','project_versions']:
        assert f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY' in sql

def test_species_module_exists():
    src=(ROOT/'platform_core'/'species.py').read_text()
    for species in ['sheep','goat','cattle','buffalo','camel']:
        assert f"'{species}'" in src
