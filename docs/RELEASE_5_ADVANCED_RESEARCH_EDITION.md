# Methane Phenotype Analytics Platform — Release 5.0

## Scope

Release 5.0 consolidates the platform-hardening, advanced statistical analysis, predictive diagnostics, longitudinal analysis, and reproducibility workstreams into one integrated research edition. It extends the Release 1–4 baseline without replacing the existing Streamlit application, project workspace, dataset catalogue, analysis registry, or publication suite.

## Implemented in this package

### Advanced statistical and phenotype analysis
- Spline-additive Gaussian regression using B-spline bases and HC3 robust covariance.
- Animal-/herd-/site-level random-intercept linear mixed models.
- Extraction of between-group and residual variance components.
- Per-animal longitudinal trajectory slopes with Benjamini–Hochberg adjustment.
- Pairwise multi-trait Pearson or Spearman associations with sample sizes and FDR adjustment.
- Held-out prediction calibration and residual diagnostics.
- New Advanced Research Analytics page integrated into the shared navigation.

### Retained from the Release 1–4 baseline
- Dataset fingerprinting, readiness and non-destructive QC.
- Measurement protocol metadata and calibration/agreement diagnostics.
- Nested animal-grouped regression benchmarking.
- Run manifests, run history and metadata comparison.
- Guided workflow, research intelligence and publication suite.
- Existing species adapters, project workspace and governance modules.

## Scientific interpretation and limitations

- The spline-additive routine is a Gaussian regression using B-spline basis expansions; it is not a penalised GAM implementation. Basis dimension should be checked through sensitivity analysis.
- Random-intercept models assume the selected grouping structure and covariance specification are appropriate. Convergence, residual assumptions, singularity and design balance must be reviewed.
- Variance components are conditional on the fitted model and grouping structure; they are not automatically heritability estimates.
- Per-animal slopes are descriptive. They do not replace mixed-effects longitudinal models, and require meaningful numeric/ordinal time coding.
- Pairwise trait correlations are associations, not causal effects. Pairwise complete observations may yield different sample sizes across pairs.
- Prediction diagnostics are only interpretable as validation when predictions are genuinely held out or out-of-fold. Residual quantiles are descriptive, not guaranteed prediction intervals.
- Genetic association, genotype–phenotype integration, multi-trait genomic models, penalised GAMs, full external validation orchestration, and AI-generated scientific interpretation are not claimed as implemented in this release. They require dedicated data contracts, methods and validation.
- Multi-species architecture is retained, but each species still requires study-specific phenotype definitions, units, and measurement protocols.

## Validation

Run the test suite from the project root:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

Run the Streamlit application:

```bash
python -m streamlit run app.py
```

A clean-environment test and browser-based UI verification should be completed in the deployment environment. The build checks performed for this package are recorded in the accompanying release summary.
