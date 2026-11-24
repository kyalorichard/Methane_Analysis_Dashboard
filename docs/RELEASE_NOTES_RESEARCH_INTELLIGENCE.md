# Methane Phenotype Analytics — Research Intelligence Update

## Added
- Research command centre with measurement protocol capture, dataset readiness, QC review queue, calibration diagnostics, phenotype evidence matrix and data-driven analysis recommendations.
- Eight-stage guided research pathway.
- Reorganised sidebar navigation.
- Nested animal-grouped regression cross-validation with inner-fold hyperparameter tuning and outer-fold evaluation.
- Analysis-run comparison page.
- Stronger dataframe content fingerprinting and enriched integrated-analysis manifests.
- Unit tests for the new research-intelligence functions.

## Scientific safeguards
- QC is non-destructive; flags are review prompts, not automatic exclusions.
- Negative-value screening is opt-in and must be justified by measurement scale.
- Calibration requires paired reference and measured values in compatible units.
- Bland–Altman and regression diagnostics do not independently establish external validity.
- Nested animal-grouped CV reduces within-animal leakage but does not replace external validation.
- The evidence matrix is exploratory and does not certify phenotype validity.

## Verification
- Python compilation: passed.
- Test suite excluding Parquet format tests: 42 passed.
- Two Parquet format tests could not run in the build environment because `pyarrow` is not installed there. The project requirements already declare `pyarrow>=15`; install project dependencies before running the complete suite.
- Streamlit visual rendering was not browser-tested in this build environment.
