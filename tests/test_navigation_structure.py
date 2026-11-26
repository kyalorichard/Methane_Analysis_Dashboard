from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_sidebar_uses_exactly_eight_research_workflow_sections():
    source = (ROOT / "analysis_engine" / "ui.py").read_text(encoding="utf-8")
    expected = [
        "01 · RESEARCH WORKSPACE",
        "02 · DATA PREPARATION",
        "03 · PHENOTYPE DISCOVERY",
        "04 · STATISTICAL INFERENCE",
        "05 · MACHINE LEARNING",
        "06 · LONGITUDINAL & EMITTER ANALYSIS",
        "07 · ADVANCED RESEARCH",
        "08 · SCIENTIFIC REPORTING",
    ]
    for section in expected:
        assert section in source


def test_every_streamlit_page_has_one_primary_navigation_entry():
    source = (ROOT / "analysis_engine" / "ui.py").read_text(encoding="utf-8")
    start = source.index("def render_sidebar_navigation():")
    end = source.index("\n        st.divider()\n        st.markdown(\"<div class='section-kicker'>Active project</div>\"", start)
    nav = source[start:end]
    targets = re.findall(r'\("[^\"]+",\s*"(pages/[^\"]+\.py|app\.py)"', nav)
    assert len(targets) == len(set(targets)), "A page is exposed more than once in primary navigation"
    expected_pages = {f"pages/{p.name}" for p in (ROOT / "pages").glob("*.py")}
    assert set(targets) == expected_pages | {"app.py"}


def test_pages_32_and_33_render_the_shared_navigation():
    for filename in ("32_Release_6_Research_Integration.py", "33_Reliability_and_Agreement.py"):
        source = (ROOT / "pages" / filename).read_text(encoding="utf-8")
        assert "render_sidebar_navigation()" in source
