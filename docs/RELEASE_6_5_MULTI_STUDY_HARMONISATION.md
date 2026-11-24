# Release 6.5 — Multi-study harmonisation and meta-analysis

## New capabilities
- Explicit source-to-canonical column mapping for study extracts.
- Explicit, user-supplied linear unit conversion (multiplier and offset); no unit inference.
- Study-level provenance fields: study ID, species, phenotype, definition, unit, method, instrument, calibration reference and conversion parameters.
- Exact protocol metadata comparability screen.
- DerSimonian–Laird random-effects pooling from independent study effect estimates and standard errors, with pooled estimate, confidence interval, Q, tau-squared and I-squared.
- Streamlit page `pages/35_Multi_Study_Harmonisation_Meta_Analysis.py`.

## Scientific interpretation
The protocol audit is a metadata screen, not proof of biological equivalence. Similar names or units do not establish that methane outcomes measure the same construct. Cross-species pooling requires a defensible common estimand and validated scale transformation. The conversion tool applies only a user-specified linear conversion and does not validate it.

The meta-analysis accepts effect estimates and standard errors; it does not derive effect sizes from raw animal-level records. Effects must be independent across studies and represent the same interpretable quantity. DerSimonian–Laird can be unstable with few studies; report study-level effects and perform sensitivity analyses, including REML where appropriate. This release does not implement multilevel/multivariate meta-analysis or meta-regression.

## Validation
Run `python -m pytest -q tests/test_study_harmonisation.py` and the full test suite. Streamlit browser workflow testing remains a separate deployment validation step.
