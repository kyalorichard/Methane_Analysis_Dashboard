# Phase 6 — Scientific reporting and publication readiness

## Purpose

Phase 6 extends the Scientific Publication Suite with editable Word and PDF reports and a complete archival ZIP. It is a reporting and reproducibility layer over the selected active dataset; it does not replace statistical analysis, protocol review, or manuscript peer review.

## New implementation

- `analysis_engine/scientific_reports.py` provides `build_scientific_report`.
- `pages/27_Scientific_Publication_Suite.py` exposes report generation and download controls.
- Word output (`.docx`) is editable and contains study metadata, methods, descriptive results tables, outcome-distribution and optional group boxplot figures, limitations, and a dataset fingerprint.
- PDF output is generated with ReportLab Platypus and includes the same core report content.
- The ZIP includes the Word/PDF documents, manifest, interpretation notes, PNG figures, CSV tables, and an Excel workbook.
- The original descriptive publication bundle remains available for backwards compatibility.

## Analysis and reporting rules

- Outcome values are coerced to numeric; non-numeric and non-finite values are excluded from outcome summaries.
- A minimum of three finite outcome observations is required.
- When an animal identifier is supplied, numeric fields are aggregated by animal-level median and categorical fields by first observed value for independent-unit group summaries and exploratory Spearman correlations.
- Source record count and analysis-unit count are reported separately.
- Reports are explicitly descriptive. They do not automatically insert inferential model results, p-values, significance stars, causal language, or unsupported conclusions.
- Concentration/AUC proxies are not reported as methane mass flux without validated calibration.
- The SHA-256 fingerprint identifies dataframe content and row order; it does not archive or replace governed source data.

## Validation

Automated tests verify DOCX/PDF creation, document text extraction, ZIP members, manifest validity, table exports, missing outcome rejection, insufficient finite observations, and invalid selected columns. The build also runs Python compilation and the full applicable test suite. Live Streamlit browser, production object storage, and cloud database integrations are not exercised by these unit tests.

## Required investigator review

Before submission, researchers must verify study title, species, measurement units, calibration, sampling protocol, animal-level independence, inclusion/exclusion rules, phenotype definition, statistical model choice, diagnostics, multiplicity family, references, and institutional/journal reporting requirements. Figures are generated from the selected active dataset and are descriptive; they do not substitute for model-based effect plots where those are required.

## Dependencies

The project requirements now include `python-docx` and `reportlab`. Install the updated requirements before using Word/PDF export in an existing deployment.

## Build verification (26 November 2026)

- `python -m compileall -q .` — passed.
- `pytest -q --ignore=tests/test_dataset_formats.py` — **176 passed, 15 warnings**.
- The two dataset-format tests were excluded because PyArrow was not available in the build environment; `pyarrow>=15` remains declared in `requirements.txt`.
- Remaining warnings originate from pre-existing numerical square-root handling, statsmodels convergence/boundary diagnostics, and scikit-learn resource warnings in other test modules. The Phase 6 report-generation tests complete without warnings.
- ZIP archive integrity was checked after packaging. No live Streamlit browser or production cloud integration test was run.
