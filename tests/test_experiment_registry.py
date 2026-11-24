import json
from analysis_engine import experiment_registry as reg


def test_scoped_settings_persist_and_isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    cfg={"schema_version":2,"models":{"RF":{"n_estimators":10}}}
    reg.save_settings("u1","p1","cattle",cfg)
    got, stamp=reg.load_settings("u1","p1","cattle")
    assert got==cfg and stamp
    assert reg.load_settings("u1","p1","sheep")== (None,None)
    assert reg.load_settings("u2","p1","cattle")== (None,None)


def test_experiment_registry_roundtrip_and_user_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYSIS_REGISTRY_PATH", str(tmp_path / "registry.sqlite3"))
    eid=reg.save_experiment("u1","p1","goats","trial",{"seed":4},[{"model":"OLS","RMSE":1.2}],[{"A":"OLS"}],{"n":20})
    items=reg.list_experiments("u1","p1","goats")
    assert len(items)==1 and items[0]["experiment_id"]==eid
    detail=reg.get_experiment(eid,"u1")
    assert detail["config"]=={"seed":4}
    assert reg.get_experiment(eid,"u2") is None
