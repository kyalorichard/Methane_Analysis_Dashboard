# Release 6.8.2 — Advanced ML page layout and navigation refinement

## Changes
- Moved the Advanced ML & Explainability page's target, grouping-unit, predictor and random-seed controls from the global sidebar into a clearly labelled main-page configuration panel.
- Reorganised navigation into seven collapsible groups: Workspace; Data & Phenotyping; Phenotype Evidence; Statistics & Machine Learning; Longitudinal & Multi-Study; Reporting & Governance; Platform Settings.
- Added direct navigation links for multi-study harmonisation, advanced ML validation and analysis/model settings.
- Applied compact, consistent styling to navigation groups.
- Reused the shared navigation renderer on the landing page to avoid a different navigation taxonomy there.

## Verification
- Python compilation: passed.
- Navigation target audit: all referenced page files exist.
- Streamlit browser rendering: not verified in this build environment.
- Analytical functions and model behaviour are unchanged by this UI-only release.
