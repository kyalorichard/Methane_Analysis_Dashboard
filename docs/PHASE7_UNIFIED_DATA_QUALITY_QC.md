# Phase 7 — Unified Data Quality & QC Centre

## Scope delivered

This release consolidates general dataset and phenotype QC into one shared engine and one Data Preparation page.

### Phase A — Shared engine

`analysis_engine/quality_control.py` provides:
- Structural checks: empty datasets, duplicate/blank column names, exact duplicate rows and fully empty rows.
- Variable-level missingness summaries.
- Numeric integrity checks for non-finite values and constant variables.
- IQR-based potential outlier screening with configurable fence multiplier.
- User-defined numeric minimum/maximum rules with rationale/source metadata.
- Animal identifier completeness, repeated/single-record animal counts and duplicate animal-time keys.
- Dataset fingerprint, engine version, severity summary and a transparent screening score.

The engine does not mutate the input DataFrame, impute values, delete records or declare observations biologically invalid.

### Phase B — Central UI

`pages/01_Data_Quality_QC_Centre.py` is the primary QC interface under Data Preparation. It includes overview/findings, integrity/missingness, phenotype distribution screening, repeated-measure structure, investigator decisions, and reproducibility exports.

### Phase C — Migration / duplicate UI removal

- The former `01_Data_Management.py` was renamed to `01b_Data_Import_and_Mapping.py` and now handles source inspection and variable mapping only.
- Configurable phenotype QC controls were removed from Research Model Lab; model-specific CV and convergence diagnostics remain there.
- General dataset integrity QC was removed from Research Diagnostics & Methods; longitudinal models, clustering and provenance remain.
- Integrated Analysis Centre now displays the central QC report when available rather than presenting a second independent QC result set.
- Phenotype validity association analysis remains a specialised scientific validation workflow, not a duplicate general-purpose QC screen.

### Phase D — Workspace and analytical integration

- Shared workspace context surfaces the last central QC severity summary.
- Project/dataset switching clears stale QC report and decision state.
- The QC Centre fingerprints the active dataset and reruns checks when the data, rules, outlier settings, animal ID or time key change.
- Analytical modules continue to own model-specific diagnostics (cross-validation, residuals, convergence and external validation).

### Phase E — History and reproducibility

- QC runs and recorded decisions are written to the existing tenant/user/project-scoped analysis run registry when the configured metadata backend is available.
- The QC Centre lists saved QC runs from the active project scope.
- Range dispositions record selected row positions, original and replacement values, method, rule limits, dataset fingerprint, rationale and timestamp.
- The QC working copy can be explicitly activated for analysis; it can then be saved as a new immutable project dataset version through Data Preparation Studio.
- Downloadable ZIP package contains `manifest.json`, `qc_findings.csv`, `missingness_profile.csv` and `investigator_decisions.csv`; when a working copy exists it also includes `qc_adjusted_analysis_copy.csv` and `qc_disposition_actions.json`.
- Manifest records engine version, dataset fingerprint, project/dataset context, rules, settings, findings, limitations and decisions.

## Operational limitations

- QC decision annotations, custom rules and the unactivated QC working copy are session state; saved QC runs are project-scoped registry records, and the ZIP is the portable complete record. After activating the QC-adjusted copy, use Data Preparation Studio to save it as a new durable project dataset version.
- A cloud registry save requires an active project and working PostgreSQL configuration. If it is unavailable, the page reports the save failure and keeps the report/decision in session state for export.
- The score is a heuristic triage aid, not a validated scientific data-quality index.
- IQR outliers are distribution-based signals, not universal biological reference ranges. Study-specific thresholds require protocol justification.
- Median estimation is a simple replacement strategy, not a model-based inferential imputation. It may attenuate variance and relationships. Within-animal interpolation is suitable only where a smooth trajectory is scientifically defensible; it should not be used for abrupt biological transitions or irregular processes without justification.
- No live browser or production PostgreSQL/S3 integration test was performed in this environment.


## QC disposition extension: winsorization (2026-11-27)

The range-validation decision workflow also supports **Winsorize selected observations**. The investigator selects flagged row positions and lower/upper empirical quantiles (defaults: 5th and 95th percentiles). Thresholds are calculated from the remaining finite, unselected observations that pass the configured range; selected values are capped to those thresholds in the separate QC working copy. Rows are retained. The audit records selected positions, original and replacement values, quantiles, derived bounds, variable, dataset fingerprint, project, timestamp and rationale. The source dataset is not modified.

Winsorization is a sensitivity/data-treatment decision, not proof that a value is erroneous. Quantiles and donor population must be justified for the study; report the method and compare key results with the unmodified data. At least two valid unselected donor observations are required. This implementation applies to selected flagged observations rather than automatically changing every tail observation in the variable.
