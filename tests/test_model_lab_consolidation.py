from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_model_lab_contains_standard_and_nested_grouped_regression_workflows():
    source = (ROOT / "pages" / "34_Advanced_ML_Explainability.py").read_text(encoding="utf-8")
    assert 'get_service("grouped_regression")' in source
    assert 'get_service("nested_grouped_regression")' in source
    assert "model_lab_run_regression" in source
    assert "model_lab_run_nested_regression" in source


def test_legacy_regression_page_is_a_compatibility_route_not_a_second_model_form():
    source = (ROOT / "pages" / "04_ML_Benchmarking.py").read_text(encoding="utf-8")
    assert "pages/34_Advanced_ML_Explainability.py" in source
    assert "get_service(\"grouped_regression\")" not in source
    assert "nested_grouped_regression" not in source


def test_legacy_workbench_and_model_pages_route_to_canonical_destinations():
    checks = {
        "17_Scientific_Analysis_Workbench.py": ["pages/33_Reliability_and_Agreement.py", "pages/31_Advanced_Inference.py"],
        "25_Research_Model_Lab.py": ["pages/34_Advanced_ML_Explainability.py", "pages/03_Statistical_Models.py"],
        "11_Advanced_Analysis.py": ["pages/31_Advanced_Inference.py"],
    }
    for filename, targets in checks.items():
        source = (ROOT / "pages" / filename).read_text(encoding="utf-8")
        for target in targets:
            assert target in source
