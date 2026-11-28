from pathlib import Path

from analysis_engine.navigation import (
    PRIMARY_NAVIGATION_GROUPS,
    SPECIALIST_NAVIGATION_GROUP,
    navigation_targets,
)

ROOT = Path(__file__).resolve().parents[1]


def test_all_navigation_targets_exist():
    for target in navigation_targets():
        assert (ROOT / target).is_file(), f"Missing navigation target: {target}"


def test_primary_navigation_has_no_duplicate_destinations():
    targets = navigation_targets(include_specialist=False)
    assert len(targets) == len(set(targets))


def test_specialist_pages_are_not_duplicated_in_primary_navigation():
    primary = set(navigation_targets(include_specialist=False))
    specialist = [target for _, target, _ in SPECIALIST_NAVIGATION_GROUP[1]]
    assert primary.isdisjoint(specialist)


def test_primary_navigation_groups_are_named_and_nonempty():
    assert len(PRIMARY_NAVIGATION_GROUPS) == 8
    assert all(name and links for name, links in PRIMARY_NAVIGATION_GROUPS)
