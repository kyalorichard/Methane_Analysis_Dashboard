# Phase 5 — Advanced Inference and Robustness

## Scope

Phase 5 adds complementary population-average inference and sensitivity analysis to the Phase 4 animal-level mixed-effects workflow. It does not replace mixed models or claim causal identification.

## New methods

1. **Gaussian GEE:** population-average marginal mean associations with independence or exchangeable working correlation and robust sandwich covariance. Requires at least five clusters in software validation; substantially more independent clusters are preferable for reliable sandwich inference.
2. **Cluster-robust OLS:** linear mean model with animal/cluster sandwich covariance and finite-sample correction. This is a covariance sensitivity analysis, not a remedy for confounding or model misspecification.
3. **Missingness audit:** variable-level missingness, joint missingness patterns, complete-case count, and optional cluster-level missingness summaries. This is descriptive and does not test or establish MCAR, MAR, or MNAR.
4. **Delta-adjusted outcome sensitivity:** hypothetical shifts to missing outcomes, expressed in pooled observed outcome SD units, with group means and record-weighted contrasts. These are transparent pattern-mixture scenarios, not recovered outcomes or an identified MNAR model.
5. **Multiplicity adjustment:** Benjamini–Hochberg, Benjamini–Yekutieli, Holm, Bonferroni, Šidák, and Holm–Šidák. The analyst must define the hypothesis family before adjustment.

## Interpretation boundaries

- GEE targets population-average effects/associations; mixed-effects models generally parameterize subject-specific conditional effects. Coefficients need not coincide.
- Robust sandwich inference relies on independent clusters and asymptotics in the number of clusters. A small cluster count can invalidate nominal standard errors and p-values.
- Cluster-robust OLS does not control unmeasured confounding.
- Missingness summaries cannot distinguish MCAR/MAR/MNAR. Delta sensitivity results depend on analyst-chosen shifts and are record-weighted.
- Multiple-testing adjustment controls a stated error criterion for the supplied family; it does not correct selective reporting or a poorly defined family.
- The existing animal-level bootstrap contrast remains the animal-level resampling method for group means. It should not be confused with record-weighted GEE estimates.

## UI

The Advanced Inference page adds tabs for population-average GEE / cluster-robust OLS, missingness and delta sensitivity, and multiple-testing correction. Results can be downloaded as text or CSV.

## Validation

Automated tests cover clustered GEE, cluster-robust covariance, low-cluster rejection, missingness patterns, delta sensitivity, and p-value adjustment. A successful unit test is not a substitute for study-specific design review, residual assessment, or live production/cloud validation.
