# Phase 3 — Variance-component reliability

Release date: 26 November 2026

## Scope

Phase 3 extends the canonical reliability engine with a model-based reliability estimand for long-format and unbalanced repeated-measurement data.

### 1. Random-intercept variance-component ICC

The new `estimate_mixed_model_icc` service fits a Gaussian animal-level random-intercept mixed model and reports:

- Between-animal random-intercept variance.
- Residual variance.
- ICC = subject variance / (subject variance + residual variance).
- A subject-cluster bootstrap confidence interval.
- Number of animals and records retained after requiring repeated observations.
- Convergence status and explicit model interpretation cautions.

An optional occasion variable enters as a fixed effect. This adjusts the expected phenotype mean by occasion; it does not estimate a random occasion variance component.

### 2. Dashboard integration

The Reliability & Agreement page now has a separate variance-component section for unbalanced long-format records. The existing balanced-panel ICC(1)/ICC(2)/ICC(3) workflow and Bland–Altman workflow remain distinct and unchanged in their estimands.

### 3. Interpretation boundaries

- This is a consistency-style random-intercept ICC conditional on any included fixed occasion effects.
- It is not interchangeable with the balanced-panel ICC(2) absolute-agreement or ICC(3) consistency estimators.
- It assumes independent subjects and a Gaussian random-intercept model with adequate variance structure.
- The bootstrap resamples subjects, not records, preserving within-animal clustering.
- Occasion adjustment is fixed-effect adjustment; random occasion variance, crossed rater/occasion effects, heteroscedastic residuals and nested herd/site effects are not included in this increment.
- The estimate is not heritability and does not establish instrument validity.

## Validation

Unit tests cover the variance-component estimate, subject-cluster bootstrap interval, occasion adjustment and rejection of data without repeated subject observations. The complete suite should be run before deployment. Live Streamlit browser and production database/S3 integration tests remain deployment tasks.
