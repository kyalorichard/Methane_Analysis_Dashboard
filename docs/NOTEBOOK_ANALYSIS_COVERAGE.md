# Scientific analysis coverage map

The supplied source notebook, `reference/Sheep_Methane_Phenotype_Advanced_Analysis.ipynb`, is the scientific reference for the sheep workflow. The 15-module interface is a navigation and workflow layer; not every notebook analysis is fully implemented as a production analysis service yet.

| Notebook section(s) | Scientific topic | Platform module | Current implementation status |
|---|---|---|---|
| 0–2 | Environment, data loading, schema harmonisation and QC | Data Management; Species & Protocol Configuration | Basic upload, role inference, profile and QC; protocol-specific validation still requires species/instrument configuration |
| 3–4 | Phenotype construction, construct validity, correlations, repeatability and duration sensitivity | Phenotype Analysis; Repeatability; Sensitivity | Candidate signal construction and exploratory summaries; formal measurement validity and repeatability need validated estimators and protocol-specific thresholds |
| 5–6 | CBBP/non-CBBP contrasts and natural methane patterns | Group Comparisons; Descriptive Analysis | Basic group summaries; study design and confounding adjustment must be specified |
| 7–9 | High/low emitter classification, continuous prediction, SVM and feature importance | ML Benchmarking; Explainability | Grouped regression benchmark and permutation-importance workflow; classification and SVM extensions remain to be completed |
| 10–11 | ARIMA/Prophet aggregate time series and exploratory LSTM | Longitudinal Analysis; Advanced Analysis | Descriptive longitudinal summaries; ARIMA/Prophet/LSTM are not yet implemented |
| 12–15 | Conventional model diagnostics, robustness, publication outputs and manuscript structure | Statistical Models; Sensitivity; Reports | OLS/GEE/mixed-model workflows and export manifest; full diagnostics and manuscript automation remain to be completed |
| 16 | Formal conventional-versus-ML benchmark | Statistical Models; ML Benchmarking | Animal-grouped regression benchmarking; classification benchmark and nested tuning require further implementation |
| 17.1–17.15 | Animal profiles, PCA, clustering, stability, PERMANOVA, transitions, SHAP, nested grouped CV and calibration | PCA & Clustering; Explainability; Longitudinal Analysis | Exploratory animal-level PCA/clustering; stability, PERMANOVA, SHAP, nested CV, probability calibration and transition inference remain pending |
| 18 | Reproducibility and manuscript export manifest | Reports & Exports | Dataset dictionary and run manifest; full artifact capture and immutable run registry pending |
| 19–23 | Variance components, reliability, allometry, nonlinear/quantile models, mixed models, equivalence | Repeatability; Advanced Analysis; Statistical Models; Equivalence | Basic/exploratory workflows; confirm estimands, model assumptions and clustered inference before publication |
| 24–25 | Consensus clustering, resampling robustness and longitudinal cluster transitions | PCA & Clustering; Longitudinal Analysis | Planned; not implemented as validated inference |
| 26–29 | Recording duration, interactions, integrated phenotype scorecard and interpretation safeguards | Sensitivity; Phenotype Scorecard; Reports | Duration filters and evidence register; interactions and automated evidence scoring require protocol-approved definitions |

## Cross-species extension rules

The platform includes adapter metadata for sheep, goats, cattle, buffalo, camels and an `other` category. This is a software extensibility framework, not evidence that all species share equivalent methane phenotypes. Before enabling a scientific analysis for a species, the study team must approve its animal identifier, measurement method, units, instrument, calibration, sampling duration, repeated-measure structure, QC ranges and phenotype definitions.
