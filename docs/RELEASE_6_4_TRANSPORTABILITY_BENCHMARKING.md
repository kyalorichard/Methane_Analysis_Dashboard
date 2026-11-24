# Release 6.4 — External validation, transportability and scientific benchmarking

## Scope

Release 6.4 adds an external-cohort screening and distribution-shift workflow, cluster-bootstrap uncertainty intervals for regression metrics, and paired cluster-bootstrap comparisons of prediction errors. The existing frozen regression and classification evaluation workflows remain available.

## New capabilities

- `analysis_engine.transportability.audit_external_cohort`: checks required-variable availability and overlap of supplied animal, cluster and cohort identifiers. Reports overlap counts and examples rather than silently treating a file as independent.
- `distribution_shift_report`: reports numeric standardized mean differences, categorical maximum prevalence differences and feature-specific missingness shifts.
- `cluster_bootstrap_regression`: percentile confidence intervals for MAE, RMSE, R² and mean observed-minus-predicted error, resampling clusters.
- `paired_model_comparison`: paired cluster-bootstrap differences in MAE and RMSE on identical held-out records. The first model is the reference; negative candidate-minus-reference differences favour the candidate.
- Page 34, section 10: upload an external cohort, select available identifiers, run schema/overlap audit and predictor shift diagnostics, and export the shift table.

## Recommended validation protocol

1. Prespecify the target estimand and distinguish methane production, yield and intensity. Harmonise phenotype definitions, units, instruments, calibration, sampling duration and SOPs before comparing cohorts.
2. Establish independence from study design and provenance. Use animal IDs and, where animals are nested, the highest independent unit (farm, herd, site or study) for screening and resampling.
3. Freeze the development model and all preprocessing. External evaluation must not refit, recalibrate or select features using the external outcomes. If recalibration is needed, report it as a separate model-update experiment.
4. Evaluate external performance with suitable metrics and uncertainty. Inspect error, calibration and subgroup performance; do not rely on a single aggregate score.
5. Compare conventional and ML models on the same held-out observations, target definition, predictors and resampling design. Paired differences are predictive comparisons, not evidence of causal superiority or inferential equivalence.
6. Investigate distribution shifts and missingness. SMD and prevalence differences are descriptive diagnostics; no universal threshold automatically determines transportability.

## Interpretation boundaries

- No observed identifier overlap is not proof of independent cohorts. IDs may be recoded, incomplete or drawn from related sampling frames.
- Matching column names do not establish measurement equivalence. Confirm metadata and protocols manually.
- Numeric SMD is undefined when pooled standard deviation is zero or cannot be estimated. Categorical prevalence differences depend on the observed category support.
- Cluster-bootstrap intervals assume clusters are independent and representative of the target sampling process. Resample the highest independent unit; few clusters produce unstable intervals.
- Paired model comparison requires predictions aligned to exactly the same records and order. The first supplied model is the reference.
- Distribution shift does not itself establish performance degradation, and absence of measured shift does not guarantee transportability.
- External performance is conditional on the external sample and protocol. Do not claim universal validity from one cohort.

## Validation performed

See the release handoff for the exact test and compile results from the packaged environment. Browser-based end-to-end testing is not claimed unless separately performed.
