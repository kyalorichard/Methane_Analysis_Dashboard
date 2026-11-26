"""Static ownership audit for major analytical capabilities.

Run from the repository root with: python tools/audit_functional_overlaps.py
This is an architectural inventory, not proof of statistical equivalence.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OWNERSHIP = {
    "subject_occasion_panel": {
        "canonical": "analysis_engine.reliability.build_subject_occasion_panel",
        "interfaces": ["pages/07_Repeatability_Reliability.py", "pages/33_Reliability_and_Agreement.py"],
        "status": "centralised",
    },
    "balanced_panel_icc": {
        "canonical": "analysis_engine.reliability.estimate_balanced_panel_icc",
        "compatibility_adapters": ["analysis_engine.research_methods.estimate_repeatability_icc"],
        "status": "centralised; distinct from unbalanced ICC(1,1)",
    },
    "unbalanced_long_format_icc1": {
        "canonical": "analysis_engine.reliability.estimate_long_format_icc1",
        "compatibility_adapters": ["analysis_engine.advanced.repeatability_icc"],
        "interfaces": ["pages/17_Scientific_Analysis_Workbench.py", "pages/21_Phenotype_Validation.py"],
        "status": "centralised; not interchangeable with balanced-panel ICCs",
    },
    "paired_bland_altman": {
        "canonical": "analysis_engine.reliability.bland_altman_paired",
        "compatibility_adapters": ["analysis_engine.research_methods.bland_altman_summary"],
        "status": "centralised",
    },
    "long_format_bland_altman": {
        "canonical": "analysis_engine.reliability.bland_altman_long_format",
        "compatibility_adapters": ["analysis_engine.advanced.bland_altman"],
        "status": "centralised; pairs occasions by subject before estimation",
    },
    "group_comparison": {
        "canonical": "analysis_engine.advanced.group_comparison",
        "interfaces": ["pages/08_Group_Comparisons.py", "pages/17_Scientific_Analysis_Workbench.py", "analysis_engine.standalone_pipeline"],
        "status": "shared computation; each interface must declare its analysis unit",
    },
    "quantile_regression": {
        "canonical": "analysis_engine.advanced.fit_quantile_regression",
        "compatibility_adapters": ["analysis_engine.advanced_research.fit_quantile_regression"],
        "status": "centralised",
    },
    "allometry": {
        "canonical_variants": [
            "analysis_engine.advanced.fit_allometry (covariate-adjusted log-log OLS)",
            "analysis_engine.advanced_research.fit_allometric_scaling (two-variable log-log OLS)",
        ],
        "status": "intentional methodological variants; not merged",
    },
}


def main() -> None:
    service_file = ROOT / "analysis_engine" / "service_registry.py"
    nav_file = ROOT / "analysis_engine" / "ui.py"
    report = {
        "audit_type": "functional_ownership_inventory",
        "limitations": "Static ownership map; does not prove numerical equivalence or discover every semantically similar implementation.",
        "canonical_service_registry_present": service_file.exists(),
        "workflow_navigation_present": nav_file.exists(),
        "capabilities": OWNERSHIP,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
