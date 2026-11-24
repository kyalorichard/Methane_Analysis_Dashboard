# v12 — standalone analysis capabilities

## Main addition: Integrated Analysis Centre
- New page `23_Integrated_Analysis_Centre.py` coordinates core analyses from the active dataset.
- Configurable outcome, animal ID, session/round, group and continuous covariates.
- Dataset audit, data dictionary, duplicate/empty-row checks and missingness diagnostics.
- Descriptive statistics and phenotype distribution diagnostics.
- Animal-level median aggregation for independent-unit group comparisons and associations.
- Optional Welch or Kruskal-Wallis group comparison with effect-size/pairwise output from the existing analysis engine.
- Repeated-measure diagnostics and exploratory ICC where the design supports it.
- Optional animal-grouped `GroupKFold` regression benchmark using the existing preprocessing pipelines.
- Portable ZIP results bundle: Excel workbook, CSV tables, HTML summary, JSON run summary/manifest and analysis dataset.
- Integrated Analysis Centre added to the shared navigation.

## Scientific safeguards
- ML requires a mapped animal identifier and uses grouped validation; no record-level random split.
- Animal-level aggregation is explicitly labelled and its information-loss trade-off is documented.
- Sensor methane concentration/AUC are not represented as methane mass flux without validated calibration.
- Repeatability is not heritability; ICC model selection must reflect the measurement design.
- Group comparisons are not causal evidence.

## Current boundaries
- The integrated pipeline focuses on numeric outcomes and regression benchmarks. Classification, survival/time-to-event, causal inference, mixed-model selection, multi-omics and species-specific methane calibration are not automatically selected.
- It exports model metrics and analysis outputs, not fitted estimator binaries or a fully containerised executable.
- Local dataset catalogue and analysis run history remain session-scoped unless persistent services are configured.
- AWS/Entra production services are not activated by this release.

## Validation
- Automated tests and compilation are reported in the accompanying release response.
- Browser-level user acceptance testing with the institution's actual datasets and deployment environment remains required.

## Additional standalone workflow: Data Preparation Studio
- New page `24_Data_Preparation_Studio.py` provides explicit, preview-before-apply transformations.
- Supports exact duplicate removal, fully empty row removal, text trimming, snake_case column names, selected numeric conversion and selected date parsing.
- Preserves the original uploaded dataset as a session-scoped source snapshot and records preparation actions.
- Avoids automatic imputation; parsing-induced missing values are surfaced for review.

## Automated validation
- Python compilation: all project Python files passed.
- Pytest: 30 passed, 1 benign warning in the pre-existing custom formula test (`sqrt` of a negative test input).
- Integrated pipeline tested with synthetic repeated-animal data, grouped regression validation, missing Animal ID guardrails and ZIP bundle integrity.
- Interactive browser acceptance testing with the full ICARDA dataset is still required.
