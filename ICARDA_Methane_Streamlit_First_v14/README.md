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
