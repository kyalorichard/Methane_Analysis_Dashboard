# Methane Phenotype Analytics Platform

A Streamlit research prototype for livestock methane phenotype data quality control, descriptive analysis, statistical inference, animal-grouped predictive modelling and phenotype evaluation.

## Quick start
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The sidebar allows CSV/Excel upload and includes an optional starter dataset: `data/ICARDA_sheep_methane_phenotypes.csv`.

## Modules and navigation

The sidebar groups the research tools into:
- **Workspace:** Overview, guided workflow, integrated analysis centre, projects and datasets.
- **Data preparation:** Data management/QC, data preparation studio, species protocol configuration and custom phenotype builder.
- **Explore and validate:** Descriptive analysis, phenotype analysis, repeatability, group comparisons, phenotype validation, emitter reports and longitudinal emitter tracking.
- **Model and explain:** Statistical models, ML benchmarking, clustering/PCA, explainability, longitudinal and advanced analysis, sensitivity, equivalence and phenotype scorecards.
- **Outputs:** Reports and exports.

The guided workflow page provides a recommended sequence from data import and variable mapping through phenotype validation, modelling and reporting.

See `PROTOTYPE_STATUS.md` for scientific and deployment limitations.


## Streamlit-first development

Run the Streamlit app locally first. The new `Scientific Analysis Workbench` page exposes additional advanced analyses without requiring AWS services. Keep `AUTH_MODE=development` only for local testing; do not expose this mode on a network or production deployment. See `docs/IMPLEMENTATION_STATUS.md` for scientific limitations.

For local Streamlit-first work, see `STREAMLIT_FIRST_ROADMAP.md` and `RUN_ON_WINDOWS.ps1`.

## Integrated standalone analysis

The **Integrated Analysis Centre** (page 23) runs an end-to-end analysis package from the active dataset:
- Dataset audit, missingness and variable dictionary.
- Numeric descriptive statistics and selected phenotype distribution diagnostics.
- Animal-level summaries for independent-unit comparisons when Animal ID is mapped.
- Optional group profiles and Welch/Kruskal-Wallis group tests.
- Repeated-measure/ICC diagnostics when animal ID is mapped.
- Optional predictor associations and animal-grouped regression benchmarking.
- Portable ZIP export containing an Excel workbook, CSV tables, HTML report, JSON summary/manifest and the analysis dataset.

The integrated pipeline is a coordinated analysis entry point, not a substitute for study-specific protocol review. It currently provides numeric-outcome regression benchmarking; it does not yet automatically choose a causal model, infer methane mass flux, or validate biological phenotype definitions.

### Data preparation studio
Page 24 creates a reversible, session-scoped analysis copy. Researchers can remove exact duplicate rows and fully empty rows, trim text whitespace, standardise column names, and explicitly parse selected numeric/date columns. The original source snapshot is retained in the session and can be restored. Missing-value imputation is intentionally not automatic.

## v13 research hardening
The v13 release adds a persistent local SQLite analysis-run registry, an animal-grouped classification benchmark, an animal random-intercept mixed-effects model, and configurable non-destructive QC thresholds. See `V13_RESEARCH_PLATFORM_HARDENING_RELEASE_NOTES.md` for validation details and scientific limitations. The local run registry stores metadata and summaries only, not source observations or fitted models.

## v14 — Scientific Publication Suite

The v14 release adds a Publication Suite page (`pages/27_Scientific_Publication_Suite.py`). It generates manuscript-oriented descriptive tables, animal-level group summaries, exploratory Spearman correlations, interactive Plotly figures, methods/limitations notes, an analysis manifest with a dataset fingerprint, and a starter reproduction script. The bundle can be exported as a ZIP containing CSV and Excel tables plus HTML figures.

Scientific safeguards are explicit: repeated records are aggregated to animal-level medians for independent-unit summaries when an animal identifier is supplied; concentration/AUC signals are not interpreted as methane mass flux without validated calibration; and descriptive associations are not presented as causal effects. Researcher review of protocol details, units, calibration, sampling design, inferential models and references remains necessary before manuscript submission.

## Dataset formats and canonical storage

The platform accepts CSV (`.csv`) and Apache Parquet (`.parquet` / `.pq`) uploads. Excel (`.xlsx` / `.xls`) remains supported for backward compatibility. All newly uploaded datasets saved to persistent project storage are converted to Snappy-compressed Parquet before object storage. Scientific modules continue to receive pandas DataFrames. The dataset registry records the original source format, canonical storage format, canonical SHA-256, source-file SHA-256, schema, row count and QC summary.

For existing deployments, re-apply `database/schema.sql` (or execute its additive `ALTER TABLE` statements) before using the updated project upload workflow. Existing CSV/Excel objects remain readable; new uploads are stored as Parquet.


## Research intelligence enhancements (Release 1–4)

This update adds a connected research command centre while retaining the existing analytical pages and engines.

### Release 1 — User experience and workflow
- Reorganised sidebar navigation into research-oriented groups.
- Reworked the overview landing experience and added readiness indicators.
- Added a guided eight-stage research pathway.
- Added content-addressed dataset fingerprints based on dataframe values, schema and index.
- Added clear scientific guardrails around animal-grouped validation and uncalibrated methane signals.

### Release 2 — Measurement and phenotype evidence
- Added study-level measurement metadata capture (instrument, method, units, calibration status, sampling frequency, SOP, reference and minimum duration).
- Added a non-destructive row-level QC review queue for missingness, IQR outliers, optional non-negative constraints and minimum recording duration.
- Added reference-based calibration regression, Bland–Altman bias and limits of agreement, MAE and RMSE.
- Added a candidate phenotype evidence matrix with missingness, distribution summaries, repeated-animal context and association with recording duration.
- Added rule-based analysis recommendations derived from dataset structure.

### Release 3 — Advanced modelling and validation
- Added nested animal-grouped regression cross-validation. Hyperparameter tuning is restricted to each outer training fold; outer folds provide the performance estimate.
- Added optional nested validation controls to the ML benchmarking page.
- Existing mixed-effects, GEE, repeatability, clustering, PCA, sensitivity and longitudinal modules remain available through the reorganised navigation.

### Release 4 — Reproducibility and publication workflow
- Added analysis-run comparison by stored manifest metadata and summaries.
- Added dataset fingerprint, measurement protocol, mapped roles and validation design to integrated-analysis manifests.
- Retained publication suite and integrated analysis ZIP outputs.
- Added tests for the new research-intelligence functions.

### Scientific interpretation and limitations
- QC flags are review prompts; observations are not automatically deleted.
- Negative-value checks are opt-in and should only be applied to variables whose documented measurement scale cannot be negative.
- Calibration and Bland–Altman diagnostics require paired measurements of the same quantity in compatible units. Correlation alone is not agreement, and fitted calibration is not externally validated by this page.
- The phenotype evidence matrix is exploratory. It does not calculate a universal phenotype score or certify biological validity.
- Nested grouped CV reduces leakage from repeated animal records but does not replace external validation or independent cohort testing.
- Analysis-run comparison only compares fields retained in the manifests and summaries.
- A dataset-aware generative AI assistant, full consensus-clustering stability workflow, UMAP, GAM/quantile/allometric model catalogue and automated external validation are not implemented as validated features in this release. Existing modules may support parts of these analyses, but do not interpret a navigation entry as proof of method validation.

## Release 5.0 — Advanced Research Edition

Release 5.0 adds a unified Advanced Research Analytics module for spline-additive modelling, random-intercept mixed models, variance decomposition, within-animal trajectory slopes, multi-trait associations, and held-out prediction diagnostics. It retains the Release 1–4 research intelligence, nested grouped ML validation, provenance, run registry, species adapters, and publication workflows. See `docs/RELEASE_5_ADVANCED_RESEARCH_EDITION.md` for methods, limitations and validation instructions.

## Release 5.1 — Advanced inference and scaling

Release 5.1 adds an **Advanced inference & scaling** page (`pages/31_Advanced_Inference.py`) with conditional quantile regression, log-log allometric scaling and an animal-level cluster bootstrap contrast. The bootstrap first aggregates repeated records to animal-level means and resamples animals within the selected groups. These methods have explicit assumptions and limitations; see `docs/RELEASE_5_1_ADVANCED_INFERENCE.md`.

## Release 6.0 — Complete Research Edition

Release 6.0 consolidates the prior platform releases into one integrated application. See `docs/RELEASE_6_COMPLETE_RESEARCH_EDITION.md` for implemented capabilities, scientific boundaries, validation evidence and remaining deployment gates. The Release 6 research integration page adds dataset integrity reporting, random-slope mixed models, consensus clustering and reproducibility manifests.


## Release 6.1 — Reliability and Measurement Agreement

Release 6.1 adds ICC(1)/ICC(2)/ICC(3) single- and average-measure reliability estimates with subject-level bootstrap confidence intervals, within/between-subject variance decomposition, and Bland–Altman paired-method agreement analysis. See `docs/RELEASE_6_1_RELIABILITY_AND_AGREEMENT.md` and Streamlit page `33_Reliability_and_Agreement.py`.

## Release 6.2 — Advanced ML validation and explainable AI

Release 6.2 adds a consolidated Advanced ML & Explainability page (`pages/34_Advanced_ML_Explainability.py`) for grouped learning curves, group-bootstrap feature-selection stability, optional SHAP explanations, group-split conformal prediction intervals, conventional OLS-versus-ML benchmarking, frozen-model external cohort validation, and animal-grouped classification metrics. See `docs/RELEASE_6_2_ADVANCED_ML_EXPLAINABILITY.md` for assumptions and remaining limitations. Classification probability recalibration and comprehensive out-of-fold calibration diagnostics remain partial rather than complete.


Release 6.2 requirement-by-requirement status and the Release 6.3+ backlog are documented in `docs/RELEASE_6_2_ADVANCED_ML_EXPLAINABILITY.md`. The release is an incremental research-workflow integration, not a claim that every advanced ML requirement is complete.


## Release 6.3 — Classification validation and external assessment

Release 6.3 adds nested stratified group cross-validation for classification, inner-fold hyperparameter tuning, cross-fitted sigmoid probability calibration, multiclass out-of-fold probability exports, discrimination and calibration metrics, and frozen-model external classification assessment. See `docs/RELEASE_6_3_CLASSIFICATION_VALIDATION.md` for methods, assumptions and remaining limitations.

## Release 6.4 — External validation and transportability

Release 6.4 adds an external cohort schema/identifier audit and predictor distribution-shift diagnostics to page 34, plus reusable cluster-bootstrap confidence intervals and paired model-error comparisons in `analysis_engine/transportability.py`. These are screening and uncertainty tools; they do not certify cohort independence or measurement harmonisation. See `docs/RELEASE_6_4_TRANSPORTABILITY_BENCHMARKING.md` for the recommended protocol and interpretation boundaries.


## Release 6.5 — Multi-study harmonisation and meta-analysis
Release 6.5 adds explicit study-level phenotype mapping and provenance, user-specified unit conversion, protocol comparability auditing, and DerSimonian–Laird random-effects synthesis of supplied independent study effects. The workflow is available in `pages/35_Multi_Study_Harmonisation_Meta_Analysis.py`. Cross-species pooling is not automatic: phenotype definition, units, measurement method, instrument, calibration and estimand must be justified. See `docs/RELEASE_6_5_MULTI_STUDY_HARMONISATION.md`.

## Release 6.6 — Conventional statistics versus machine learning
Release 6.6 adds a matched grouped-cross-validation comparison in `pages/34_Advanced_ML_Explainability.py`. The workflow compares OLS, GEE, random-intercept mixed-effects, spline-basis, median quantile and eligible allometric regression against selected ML estimators on identical grouped folds. It reports out-of-fold metrics, paired group-bootstrap RMSE difference intervals and downloadable prediction-level results. This is a predictive benchmark; see `docs/RELEASE_6_6_STATISTICAL_ML_COMPARISON.md` for assumptions and limitations.


## Release 6.7 — Analysis and model settings
Release 6.7 adds a central model configuration page (`pages/36_Analysis_Model_Settings.py`) for grouped validation settings and hyperparameters of Random Forest, Extra Trees, HistGradientBoosting, SVR and KNN. Settings can be exported/imported as JSON. They are session-scoped and currently feed the matched conventional-versus-ML comparison on page 34; other analysis pages retain their own controls. See `docs/RELEASE_6_7_MODEL_SETTINGS.md`.


## Release 6.8 — Persistent settings and experiment management
Release 6.8 adds a SQLite-backed settings registry scoped by user, project/study and species; nested GroupKFold random-search optimisation for supported ML estimators; conventional-model controls for GEE working correlation, mixed-effects ML/REML, quantile level and spline knots; and an experiment registry that stores configurations, metrics and paired comparisons. Set `ANALYSIS_REGISTRY_PATH` to a durable path. In production, connect user scope to the authenticated identity and use durable shared storage for multi-instance deployments. See `docs/RELEASE_6_8_PERSISTENT_SETTINGS_EXPERIMENTS.md`.

## Local-first project persistence (Release 6.9.1)

The Project Workspace now defaults to local persistent storage when the cloud
backend is not fully configured. Local mode uses SQLite metadata plus Parquet
files under `data/local_workspace/`; no PostgreSQL or S3 credentials are needed.

- `PROJECT_STORAGE_BACKEND=local` selects SQLite + filesystem storage.
- `PROJECT_STORAGE_BACKEND=cloud` selects the existing PostgreSQL + S3 backend.
- If the variable is unset, cloud mode is selected only when both `DATABASE_URL`
  and `S3_BUCKET` are present; otherwise local mode is used.
- `LOCAL_PROJECT_STORAGE_DIR` optionally changes the local data directory.

For Docker/cloud hosting, mount `data/local_workspace` (or the configured
`LOCAL_PROJECT_STORAGE_DIR`) as a persistent volume. Local mode is intended for
single-instance deployments; use PostgreSQL/S3 for concurrent multi-instance
production deployments. Back up the SQLite database and project directory
consistently, preferably while the app is stopped or using SQLite's backup API.

## Professional dashboard and consolidation update

The primary navigation is workflow-led and uses one canonical reliability/agreement workspace. Repeated-measure panel construction, balanced-panel ICCs, unbalanced long-format ICC(1,1), Bland–Altman statistics and within/between-subject variance calculations are maintained in `analysis_engine/reliability.py` and dispatched through `analysis_engine/service_registry.py`. Older function names remain as compatibility adapters. See `docs/REFACTORING_AND_PRODUCTION_READINESS.md` for the ownership map, source-data retention behavior, migration and remaining production gates.

New project uploads retain the original uploaded file separately from the canonical Parquet analysis copy. Both objects are checksummed; the project workspace provides an authorized original-source download. For cloud storage, apply `database/migrations/004_original_source_storage.sql` before deploying the updated code.
