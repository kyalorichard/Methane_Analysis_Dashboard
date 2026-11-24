# v14 — Scientific Publication and Reproducibility Suite

## New capability
- Publication Suite page for configuring a study title, dataset, species, primary numeric phenotype, animal identifier, grouping variable, covariates and protocol notes.
- Manuscript-oriented descriptive statistics and animal-level group summaries.
- Exploratory Spearman correlation table using animal-level medians when an animal ID is provided.
- Interactive Plotly outcome distribution and optional group comparison figures.
- Export bundle with CSV tables, Excel workbook, interactive HTML figures, methods/limitations notes, JSON manifest, dataset fingerprint and a starter reproduction script.

## Scientific safeguards
- Repeated observations are aggregated to animal-level medians for independent-unit group summaries and correlations.
- Report explicitly distinguishes descriptive association from causal inference.
- Instrument concentration/AUC is not converted to methane mass flux without validated calibration.
- The output is a reporting aid, not an automatically submission-ready manuscript. Protocol, units, calibration, sampling design, model diagnostics, references and interpretation require researcher review.

## Validation
- New tests cover animal-level aggregation, bundle contents and invalid outcomes.
- Full project test and compilation results are recorded in the delivery message after execution.
