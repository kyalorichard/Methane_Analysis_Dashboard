from pathlib import Path


def test_conventional_vs_ml_comparison_page_is_registered_in_navigation():
    root = Path(__file__).resolve().parents[1]
    page = root / "pages" / "38_Conventional_vs_ML_Comparison.py"
    assert page.exists()
    source = page.read_text(encoding="utf-8")
    assert "compare_grouped_models" in source
    assert "paired_comparisons" in source
    assert "oof_predictions" in source
    assert "GroupKFold" in (root / "analysis_engine" / "model_comparison.py").read_text(encoding="utf-8")

    navigation = (root / "analysis_engine" / "ui.py").read_text(encoding="utf-8")
    assert "pages/38_Conventional_vs_ML_Comparison.py" in navigation


def test_statistical_and_ml_pages_link_to_dedicated_comparison():
    root = Path(__file__).resolve().parents[1]
    target = "pages/38_Conventional_vs_ML_Comparison.py"
    assert target in (root / "pages" / "03_Statistical_Models.py").read_text(encoding="utf-8")
    assert target in (root / "pages" / "04_ML_Benchmarking.py").read_text(encoding="utf-8")
    assert target in (root / "pages" / "34_Advanced_ML_Explainability.py").read_text(encoding="utf-8")
