# Phase 4 — Longitudinal and Repeated-Measures Analytics

## Scope

Phase 4 extends the existing descriptive paired-round workflow and the separate Research Diagnostics random-slope helper. It introduces a canonical long-format Gaussian mixed-model service in `analysis_engine/longitudinal.py` and exposes it in the Longitudinal Analysis workspace.

## Capabilities

- Numeric time or date-based time converted to elapsed days from the earliest valid date.
- Unbalanced and irregular repeated observations; no artificial balancing or interpolation.
- Explicit complete-case audit for the selected outcome, subject, time, treatment and covariates.
- Random-intercept models and animal-specific linear random time slopes.
- Linear or cubic B-spline fixed time trends.
- Optional treatment/group-by-time interactions to estimate group-specific mean trajectories.
- Population-level fixed-effect predictions with Wald 95% confidence intervals.
- Residual-versus-fitted and residual-distribution diagnostics, plus a sample-size-aware Shapiro-Wilk screening statistic.
- ML-based AIC/BIC reporting and a random-intercept comparator. The UI intentionally does not apply a standard chi-square likelihood-ratio test to random-slope variance because the null is on a parameter-space boundary.
- Downloadable model audit, predicted trajectory and residual diagnostic tables.

## Statistical interpretation and boundaries

1. The model is Gaussian linear mixed effects, not a generalized mixed model. Outcomes should be continuous and reasonably compatible with the assumed conditional residual distribution.
2. The random time slope is linear even when the population fixed time trend uses a spline. A spline random-effects covariance structure is not fitted.
3. Date input is represented as elapsed days from the earliest valid date. Irregular spacing is retained; time is not rounded to nominal visits.
4. Missing values are handled by complete-case deletion for the selected model variables. Subjects without at least two distinct observed time values are excluded. The audit distinguishes rows removed for incomplete/invalid values from complete-case rows excluded because the subject has no repeated time points. This is not a missing-at-random test or an imputation procedure. Assess whether missingness is informative.
5. Predictions are population-average fixed-effect predictions at median numeric and modal categorical covariate values. Their intervals are confidence intervals for the mean trajectory, not individual prediction intervals and do not include subject-specific random effects.
6. At least five independent subjects with at least two distinct time values are required by this workflow as a pragmatic guardrail, not a universal power guarantee. Random-slope estimates need substantially more independent subjects and within-subject time information; convergence and covariance estimates must be scrutinized.
7. Residual plots and Shapiro-Wilk are diagnostic screens. They do not prove normality, independence, homoscedasticity, or correct covariance specification. Examine residual patterns over time and by subject, leverage, influential clusters, and protocol effects.
8. AIC/BIC comparisons require the same response records and likelihood basis. REML is disabled for the UI model comparisons. Random-effect variance tests can have nonstandard null distributions; no ordinary chi-square LRT is reported for the random-intercept versus random-slope comparison.
9. Treatment-by-time coefficients are conditional associations unless treatment allocation and study design justify causal interpretation. Repeated measurements do not increase the number of independent experimental units.

## Validation

Automated tests cover unbalanced records, missingness accounting, date conversion, repeated-subject eligibility, random-slope fitting, treatment-by-time predictions, spline fitting, prediction intervals and residual diagnostics. The complete non-pyarrow test suite is run during release validation. Production database/S3 and interactive browser behaviour are not exercised by the unit suite.
