"""Canonical navigation catalogue for the Methane Phenotype Analytics workspace.

Primary destinations represent the preferred user journey. Older specialist pages
remain reachable in a clearly separated compatibility section so that no analytical
capability is silently removed while workflows are consolidated.
"""
from __future__ import annotations

PRIMARY_NAVIGATION_GROUPS = (
    ("01 · RESEARCH WORKSPACE", (
        ("Research overview", "app.py", "🏠"),
        ("Projects & datasets", "pages/00_Project_Workspace.py", "🗂️"),
        ("Research overview & readiness", "pages/28_Research_Intelligence.py", "🧭"),
        ("Guided research workflow", "pages/22_Guided_Research_Workflow.py", "🗺️"),
        ("Integrated analysis centre", "pages/23_Integrated_Analysis_Centre.py", "🧪"),
        ("Analysis history", "pages/26_Analysis_Run_History.py", "🕘"),
    )),
    ("02 · DATA PREPARATION", (
        ("Data import & variable mapping", "pages/01b_Data_Import_and_Mapping.py", "📥"),
        ("Species & measurement protocol", "pages/16_Species_Protocol_Configuration.py", "🐑"),
        ("Data preparation studio", "pages/24_Data_Preparation_Studio.py", "🧽"),
        ("Data Quality & QC Centre", "pages/01_Data_Quality_QC_Centre.py", "🧹"),
        ("Phenotype construction", "pages/19_Custom_Phenotype_Builder.py", "🧬"),
    )),
    ("03 · PHENOTYPE DISCOVERY", (
        ("Descriptive analysis & distributions", "pages/02_Descriptive_Analysis.py", "📊"),
        ("Phenotype analysis", "pages/06_Phenotype_Analysis.py", "🔬"),
        ("Group comparisons", "pages/08_Group_Comparisons.py", "⚖️"),
        ("PCA & phenotype clustering", "pages/05_Clustering_PCA.py", "🧩"),
        ("Phenotype evidence scorecard", "pages/14_Phenotype_Scorecard.py", "🏅"),
    )),
    ("04 · STATISTICAL INFERENCE", (
        ("Statistical models & mixed effects", "pages/03_Statistical_Models.py", "📐"),
        ("Reliability, repeatability & agreement", "pages/33_Reliability_and_Agreement.py", "📏"),
        ("Allometry & nonlinear inference", "pages/31_Advanced_Inference.py", "📈"),
        ("Equivalence analysis", "pages/13_Equivalence_Analysis.py", "↔️"),
        ("Phenotype validity analysis", "pages/21_Phenotype_Validation.py", "✅"),
    )),
    ("05 · MACHINE LEARNING", (
        ("Unified Research Model Lab", "pages/34_Advanced_ML_Explainability.py", "🤖"),
        ("Conventional vs ML model comparison", "pages/38_Conventional_vs_ML_Comparison.py", "⚖️"),
    )),
    ("06 · LONGITUDINAL & EMITTER ANALYSIS", (
        ("Animal trajectories & repeated rounds", "pages/10_Longitudinal_Analysis.py", "📉"),
        ("Emitter cohort classification", "pages/18_Low_High_Emitter_Reports.py", "↕️"),
        ("Emitter persistence & transitions", "pages/20_Longitudinal_Emitter_Tracking.py", "🔁"),
        ("Forecasting & time-series analysis", "pages/37_Time_Series_Forecasting.py", "📈"),
    )),
    ("07 · ADVANCED RESEARCH", (
        ("Advanced research analytics", "pages/30_Advanced_Research_Analytics.py", "🧪"),
        ("Sensitivity & robustness", "pages/12_Sensitivity_Robustness.py", "🛡️"),
        ("Multi-study harmonisation & meta-analysis", "pages/35_Multi_Study_Harmonisation_Meta_Analysis.py", "🌐"),
        ("Research diagnostics & methods", "pages/32_Research_Diagnostics_and_Methods.py", "🧬"),
        ("Analysis & model settings", "pages/36_Analysis_Model_Settings.py", "⚙️"),
    )),
    ("08 · SCIENTIFIC REPORTING", (
        ("Scientific publication & reporting suite", "pages/27_Scientific_Publication_Suite.py", "📚"),
        ("Compare analysis runs", "pages/29_Analysis_Comparison.py", "🧾"),
        ("Quick reports, tables & exports", "pages/15_Reports_Exports.py", "📄"),
    )),
)

# Retained for specialist access and backward compatibility. These pages overlap
# newer canonical workflows or provide narrower/older views of the same domains.
SPECIALIST_NAVIGATION_GROUP = ("SPECIALIST / LEGACY ENTRY POINTS · CAPABILITIES RETAINED", (
    ("Legacy regression benchmarking", "pages/04_ML_Benchmarking.py", "📈"),
    ("Held-out permutation importance (specialist)", "pages/09_Explainability.py", "🔎"),
    ("Legacy classification & mixed-model lab", "pages/25_Research_Model_Lab.py", "🧬"),
    ("Within-animal trajectory view", "pages/07_Repeatability_Reliability.py", "🔁"),
    ("Advanced scientific workbench (overlapping methods)", "pages/17_Scientific_Analysis_Workbench.py", "🧰"),
    ("Advanced nonlinear analysis (legacy)", "pages/11_Advanced_Analysis.py", "🧮"),
))


def navigation_targets(include_specialist: bool = True) -> list[str]:
    groups = list(PRIMARY_NAVIGATION_GROUPS)
    if include_specialist:
        groups.append(SPECIALIST_NAVIGATION_GROUP)
    return [target for _, links in groups for _, target, _ in links]
