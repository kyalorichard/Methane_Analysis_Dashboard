import numpy as np
import pandas as pd
from analysis_engine.research_hardening import grouped_classification_benchmark, configurable_qc, fit_mixed_effects
from platform_core.run_registry import save_run, list_runs, delete_run


def repeated_data():
    rng=np.random.default_rng(5); rows=[]
    for i in range(60):
        x=rng.normal(); group="high" if x>0 else "low"; animal_effect=rng.normal(0,1)
        for visit in (1,2,3):
            rows.append({"AnimalID":f"A{i:03}","Round":f"R{visit}","x":x+rng.normal(0,.1),"phenotype":3*x+animal_effect+rng.normal(0,.3),"class":group})
    return pd.DataFrame(rows)


def test_grouped_classification_has_expected_metrics_and_confusion_matrix():
    d=repeated_data()
    scores,matrices,labels=grouped_classification_benchmark(d,"class",["x","Round"],"AnimalID",["Logistic Regression"],n_splits=3)
    assert scores.iloc[0]["n_animals"]==60
    assert "macro_f1" in scores.columns
    assert matrices["Logistic Regression"].shape==(2,2)
    assert len(labels)==2


def test_qc_flags_without_deleting_rows():
    d=pd.DataFrame({"x":[1,2,3,100,None]})
    q=configurable_qc(d,{"x":{"min":0,"max":10,"source":"protocol"}})
    assert q.iloc[0]["above_max_n"]==1
    assert q.iloc[0]["missing_n"]==1
    assert len(d)==5


def test_mixed_effects_random_intercept_model():
    d=repeated_data()
    estimates,summary=fit_mixed_effects(d,"phenotype","AnimalID",["x"],"Round")
    assert summary["n_animals"]==60
    assert "converged" in summary
    assert "estimate" in estimates.columns


def test_mixed_effects_attempts_small_animal_count_with_explicit_warning():
    rng=np.random.default_rng(12); rows=[]
    for i in range(4):
        animal_effect=rng.normal()
        for visit in range(5):
            rows.append({"AnimalID":f"A{i}","phenotype":2+0.4*visit+animal_effect+rng.normal(0,.2),"visit":visit})
    estimates,summary=fit_mixed_effects(pd.DataFrame(rows),"phenotype","AnimalID",["visit"])
    assert summary["n_animals"]==4
    assert any("fewer than five independent animals" in w for w in summary["warnings"])


def test_run_registry_roundtrip(tmp_path):
    db=tmp_path/"runs.sqlite3"
    manifest={"run_timestamp_utc":"2026-11-23T00:00:00+00:00","dataset_name":"demo","outcome":"y","species":"sheep","audit":{"data_sha256":"abc"}}
    save_run("run-1",manifest,{"n":10},db_path=db)
    rows=list_runs(db_path=db)
    assert rows[0]["run_id"]=="run-1"
    assert rows[0]["dataset_fingerprint"]=="abc"
    delete_run("run-1",db_path=db)
    assert list_runs(db_path=db)==[]


def test_run_registry_scopes_history_by_tenant_project_and_user(tmp_path):
    db = tmp_path / "scoped-runs.sqlite3"
    manifest = {"dataset_name": "sheep.parquet", "species": "sheep", "outcome": "methane", "audit": {"data_sha256": "abc"}}
    save_run("run-a", manifest, {"n": 10}, db_path=db, tenant_id="tenant-a", project_id="project-a", user_subject="user-a", dataset_id="dataset-a")
    save_run("run-b", manifest, {"n": 20}, db_path=db, tenant_id="tenant-a", project_id="project-b", user_subject="user-a")
    save_run("run-c", manifest, {"n": 30}, db_path=db, tenant_id="tenant-b", project_id="project-a", user_subject="user-b")

    assert [r["run_id"] for r in list_runs(db_path=db, tenant_id="tenant-a", project_id="project-a", user_subject="user-a")] == ["run-a"]
    assert [r["run_id"] for r in list_runs(db_path=db, tenant_id="tenant-a", user_subject="user-a")] == ["run-b", "run-a"]
    assert [r["run_id"] for r in list_runs(db_path=db, tenant_id="tenant-b", user_subject="user-b")] == ["run-c"]


def test_run_registry_keeps_legacy_unscoped_api_compatible(tmp_path):
    db = tmp_path / "legacy-runs.sqlite3"
    save_run("legacy", {"dataset_name": "old.csv", "species": "goat"}, {"n": 3}, db_path=db)
    rows = list_runs(db_path=db)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "legacy"
    assert rows[0]["tenant_id"] is None
