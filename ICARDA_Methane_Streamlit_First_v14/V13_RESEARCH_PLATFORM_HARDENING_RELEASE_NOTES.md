# ICARDA Methane Phenotype Analytics — v13 release notes

## New capabilities

### 1. Persistent local analysis-run registry
- Integrated Analysis Centre runs are recorded in a local SQLite database (`platform_data/analysis_runs.sqlite3`).
- The registry stores run ID, UTC timestamp, dataset name and fingerprint, outcome, species, status, configuration manifest and summary metadata.
- Raw observations, full analysis tables and fitted model binaries are not stored in the registry.
- Registry location can be changed with `METHANE_RUN_REGISTRY`.
- New Analysis Run History page supports inspection of saved manifests and summaries.

### 2. Animal-grouped classification benchmark
- Logistic Regression, Random Forest, Extra Trees and HistGradientBoosting.
- StratifiedGroupKFold keeps all records for an animal in one fold.
- Imputation, scaling and categorical encoding are fitted inside each training fold.
- Reports accuracy, balanced accuracy, macro/weighted F1, macro precision/recall and pooled out-of-fold confusion matrices.
- Does not report ROC-AUC until fold-level probability alignment and class support are validated. Use balanced accuracy and macro-F1 for imbalanced outcomes.

### 3. Repeated-measures mixed-effects model
- Gaussian linear mixed model with an animal-level random intercept.
- Optional fixed effects and categorical session/round term.
- Reports fixed-effect estimates, standard errors, z statistics, p-values, confidence intervals, random-intercept variance, residual variance and convergence diagnostics.
- Uses alternative optimizers when the default optimizer fails on a near-boundary/singular covariance estimate.
- Requires at least five animals and repeated observations. Convergence and model assumptions must be reviewed; results are associations, not causal effects.

### 4. Configurable QC rule evaluation
- User-defined minimum/maximum screening thresholds for numeric phenotypes.
- Reports out-of-range and missing counts without silently removing records.
- Each threshold can record its protocol/instrument rationale. Thresholds are not universal biological reference intervals.

## Validation
- Python compilation: passed.
- Pytest: 34 passed; one benign warning remains in the existing custom formula test for square-root of negative values.
- Actual dataset smoke test (`20261112_OldLMD_Phenotype_Data_RO(1).csv`, 1,740 records / 595 animals): grouped Breed classification using weight, Sex and Round completed. Logistic Regression achieved 72.4% accuracy, 72.1% balanced accuracy and 0.717 macro-F1; Extra Trees achieved 64.3% accuracy, 62.9% balanced accuracy and 0.629 macro-F1 under three-fold animal-grouped validation. Mixed-effects model for mean_methane with weight, Breed and Round also completed (1,740 records; 595 animals; convergence reported). These are dataset-specific internal validation results, not external validation.
- Synthetic tests cover grouped classification, mixed-effects estimation, QC flags and SQLite registry round-trip.

## Important limitations
- Local SQLite registry is single-host local persistence; it is not multi-user PostgreSQL, tenant isolation or an access-control system.
- No automatic backup/restore interface is included. Back up the registry file and protect it as research metadata.
- Classification is only valid when the target definition is scientifically meaningful and predictors are available at the intended prediction time. Avoid leakage and repeated-measure confounding.
- Mixed-effects estimates depend on outcome distribution, random-effects structure, residual assumptions and model convergence. Inspect residual diagnostics and consider alternative structures where justified.
- This release is a local-first Streamlit research platform. Entra ID, AWS, background workers and production database infrastructure still require separate deployment/configuration and security review.
- Browser/mobile user acceptance testing has not been completed.
