from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_methods_page_has_neutral_user_facing_name():
    page = ROOT / "pages" / "32_Research_Diagnostics_and_Methods.py"
    assert page.exists()
    source = page.read_text(encoding="utf-8").lower()
    assert "research diagnostics & methods" in source
    assert "release 6" not in source


def test_sidebar_uses_neutral_research_methods_label():
    source = (ROOT / "analysis_engine" / "navigation.py").read_text(encoding="utf-8").lower()
    assert "research diagnostics & methods" in source
    assert "32_release_6" not in source


def test_legacy_module_is_only_a_compatibility_shim():
    source = (ROOT / "analysis_engine" / "release6.py").read_text(encoding="utf-8")
    assert "from .research_methods import *" in source
