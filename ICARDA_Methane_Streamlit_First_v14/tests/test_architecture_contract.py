from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_tenant_schema_contains_rls():
    sql = (ROOT / "database" / "schema.sql").read_text()
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.tenant_id" in sql

def test_compose_has_core_services():
    compose = (ROOT / "docker-compose.production.yml").read_text()
    for service in ["postgres:", "redis:", "minio:", "api:", "worker:", "dashboard:"]:
        assert service in compose

def test_auth_is_not_claimed_as_complete():
    auth = (ROOT / "infra" / "REVERSE_PROXY_AUTH.md").read_text()
    assert "remain implementation tasks" in auth
