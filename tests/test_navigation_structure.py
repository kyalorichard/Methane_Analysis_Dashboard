from pathlib import Path

from analysis_engine.navigation import (
    PRIMARY_NAVIGATION_GROUPS, SPECIALIST_NAVIGATION_GROUP, navigation_targets,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sidebar_uses_eight_research_workflow_sections():
    expected = [
        "01 · RESEARCH WORKSPACE", "02 · DATA PREPARATION",
        "03 · PHENOTYPE DISCOVERY", "04 · STATISTICAL INFERENCE",
        "05 · MACHINE LEARNING", "06 · LONGITUDINAL & EMITTER ANALYSIS",
        "07 · ADVANCED RESEARCH", "08 · SCIENTIFIC REPORTING",
    ]
    assert [name for name, _ in PRIMARY_NAVIGATION_GROUPS] == expected


def test_every_page_is_reachable_exactly_once_across_primary_and_specialist_navigation():
    targets = navigation_targets()
    assert len(targets) == len(set(targets))
    expected_pages = {f"pages/{p.name}" for p in (ROOT / "pages").glob("*.py")}
    assert set(targets) == expected_pages | {"app.py"}


def test_specialist_routes_are_not_in_primary_navigation():
    primary = set(navigation_targets(include_specialist=False))
    specialist = {target for _, target, _ in SPECIALIST_NAVIGATION_GROUP[1]}
    assert primary.isdisjoint(specialist)


def test_pages_32_and_33_render_the_shared_navigation():
    for filename in ("32_Research_Diagnostics_and_Methods.py", "33_Reliability_and_Agreement.py"):
        source = (ROOT / "pages" / filename).read_text(encoding="utf-8")
        assert "render_sidebar_navigation()" in source
