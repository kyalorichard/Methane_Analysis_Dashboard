# Methane Phenotype Analytics Platform 6.0 — Complete Research Edition

## Release objective

Release 6.0 consolidates the existing Release 1–5.1 application and the integrated research roadmap into one maintained codebase. Existing pages and analytical modules are retained; the release adds an integrated research page and new reusable analysis functions.

## Added in this consolidation

- Dataset integrity reporting for structural issues, duplicate rows, missing cells, fully empty rows and non-finite numeric values.
- Gaussian random-intercept/random-slope mixed-effects modelling for repeated observations, with grouping unit selectable by the researcher.
- Consensus K-means clustering using repeated subsampling, a co-association matrix and final hierarchical clustering of consensus distances.
- Frozen-estimator external regression validation utility. It evaluates an already fitted estimator and never refits it on external data.
- Group-aware learning-curve utility.
- Group-bootstrap feature-selection stability utility for estimators exposing feature importances.
- JSON reproducibility manifest containing dataset fingerprint, analysis parameters, software versions and seed.
- Streamlit integration page: `pages/32_Release_6_Research_Integration.py`.

## Retained capabilities

The release retains the prior project workspace, data preparation and QC, species adapters, protocol metadata, phenotype builder, repeatability diagnostics, PCA and clustering workflows, grouped regression/classification benchmarking, nested grouped regression CV, permutation explainability, publication outputs, run registry, research intelligence, advanced spline-additive analysis, random-intercept mixed models, quantile regression, allometric scaling, animal-level bootstrap contrasts and descriptive within-animal slopes.

## Requirements and scientific boundaries

- The existing spline-additive regression uses B-spline basis expansion with HC3 covariance. It is not a penalised GAM/GAMM.
- The random-slope model is a Gaussian linear mixed model. It is not a nonlinear mixed-effects model.
- Consensus clustering is an exploratory stability method. Evaluate cluster number, feature scaling, missing-data handling and sensitivity to resampling settings.
- External validation requires an estimator trained and frozen before accessing independent data. The utility does not establish independence of sites/herds or protocol harmonisation.
- Feature selection stability is implemented as a reusable utility; it requires a suitable estimator and externally prepared predictor matrix. It is not yet a universal one-click workflow for every model family.
- Genotype–phenotype association, genomic relationship matrices, heritability estimation and genetic/environmental covariance models are not implemented in this release.
- SHAP is not bundled as a mandatory dependency. Existing permutation-based explainability remains available; SHAP integration remains a separately gated optional capability.
- Dataset-grounded conversational AI is not implemented. Do not interpret the reproducibility manifest as a full immutable audit trail.
- S3/PostgreSQL persistence and tenant security require institution-specific integration and deployment testing. Local SQLite run history is not a substitute for validated production recovery.

## Validation performed for this package

- Python compilation across the repository.
- Automated unit tests, including Release 6 random-slope, consensus clustering, external validation and provenance tests.
- Existing tests excluding Parquet-dependent tests where `pyarrow` is unavailable.
- ZIP archive integrity check.

Browser-based Streamlit end-to-end testing, production database/S3 integration, backup restoration, security review, load testing and deployment-specific external validation remain operational release gates.

## Launch

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

For complete Parquet test coverage, install the declared `pyarrow` dependency before running the full suite.
