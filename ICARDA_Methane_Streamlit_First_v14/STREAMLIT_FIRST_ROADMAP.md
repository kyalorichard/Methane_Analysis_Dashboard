# Streamlit-first development plan

## Current increment (v4)
- Retains the 16 existing Streamlit pages and the supplied sheep dataset.
- Adds Scientific Analysis Workbench with ICC(1,1)/ICC(1,k) exploratory reliability, animal bootstrap interval, Bland–Altman agreement, Welch/Kruskal group inference with BH adjustment, log-log allometry, quantile regression, recording-duration sensitivity, independent-group TOST and exploratory bootstrap cluster stability.
- Adds JSON analysis manifest and Parquet dataset export.
- Adds automated tests for advanced workflows.

## Run locally
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```
Local development uses `AUTH_MODE=development`. This is a local-only bypass and must never be used for a shared or public deployment.

## Next Streamlit increments
1. Implement a full ML benchmark page: regression and classification, animal-grouped nested CV, fold-level metrics, calibration and leakage checks.
2. Implement variance-component reliability models with explicit ICC estimands and uncertainty.
3. Implement longitudinal mixed-effects models, nonlinear splines, interaction analyses and residual diagnostics.
4. Implement cluster validation: consensus clustering, bootstrap stability with out-of-bag prediction, PERMANOVA and transition analysis.
5. Implement reproducible analysis-run registry, project-level local storage, versioned dataset transformations and one-click report bundles.
6. Implement multi-species protocol approval gates and unit/calibration validation per species.
7. Only after local UAT, connect institutional Entra authentication and persistent AWS services.

## Scientific limitations
- ICC(1,1) is a one-way random-effects exploratory estimate. For fixed sessions or a fully crossed repeated-measures design, specify and implement the appropriate two-way ICC model.
- Welch/Kruskal tests assume independent units. Repeated animal records should be aggregated at the animal level for simple independent-group tests or analysed with GEE/mixed models.
- TOST requires a justified equivalence margin specified before inspecting results.
- Bootstrap cluster ARI is exploratory; use a prespecified resampling design and out-of-bag assignment for publication-grade stability.
- Quantile regression and allometry require diagnostics, prespecified covariates and careful interpretation.
- Methane concentration and AUC are instrument-derived signals; they are not methane mass flux without validated calibration.
- No goat, cattle, buffalo or camel methane phenotype definition is scientifically validated by the presence of an adapter template.

## v6 additions — optional clustering and variable importance
- Clustering/PCA now supports selecting all or a subset of K-means, Agglomerative, Gaussian mixture, and DBSCAN algorithms. The page reports silhouette, Davies–Bouldin, Calinski–Harabasz, cluster counts, and DBSCAN noise points, with downloadable animal-level assignments.
- Explainability now supports all or selected regression models from the ML benchmark suite and computes held-out, animal-grouped permutation importance for each model. Model metrics and per-model importance tables are downloadable.
- Variable importance is predictive/model-dependent, not causal. The current implementation uses one grouped holdout; repeated grouped resampling should be used for publication-grade stability intervals.
- Existing ML benchmarking continues to support optional regression model selection.


## v7 addition: Low/high emitter reports
A percentile-driven Low & High Emitter Assessment page supports phenotype selection, 1–25% lower/upper tails, animal-level median/mean aggregation, minimum repeated-record thresholds, group profiles, CSV assignments and multi-sheet Excel reports. See `LOW_HIGH_EMITTER_REPORTS.md`.
