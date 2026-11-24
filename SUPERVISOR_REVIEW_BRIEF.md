# Methane Phenotype Analytics Platform
## Supervisor discussion prototype — concept and review brief

### Purpose
This prototype demonstrates a unified analytical workspace for evaluating methane-related phenotypes in livestock research. It is based on the analytical workflow specified in the *Sheep Methane Phenotype Advanced Analysis* notebook and is being designed for extension across sheep, goats, cattle, buffalo, camels and other livestock species.

### Research problem
Methane datasets often contain repeated animal records, heterogeneous measurement durations, multiple candidate signal-derived traits and a mixture of animal, management and recording metadata. A defensible phenotype evaluation therefore requires more than a single prediction model. It should assess measurement validity, repeatability, biological associations, longitudinal behaviour, predictive performance and robustness.

### Prototype workflow
1. Data import and structural quality control.
2. Candidate phenotype construction and duration-normalised measures.
3. Descriptive statistics, missingness and correlation analysis.
4. Conventional modelling: OLS with robust standard errors, GEE and animal-level mixed-effects models.
5. ML benchmarking: Ridge, Elastic Net, KNN, SVR, Random Forest, Extra Trees and HistGradientBoosting, using grouped cross-validation by animal.
6. Animal-level PCA and K-means clustering diagnostics.
7. Planned extensions: repeatability/ICC and variance components, group contrasts, model explainability, longitudinal analysis, allometric scaling, spline and quantile regression, equivalence testing, sensitivity analysis, consensus clustering, cluster transitions, integrated phenotype scorecard and reproducible report exports.

### Demonstration dataset
The package includes a clearly labelled synthetic sheep dataset (120 animals × 3 rounds = 360 records). It exists only to demonstrate navigation and analytical execution. It is not empirical ICARDA/CBBP data and must not be used to draw biological or programme conclusions.

### Scientific safeguards
- Animal-level grouping is used for predictive validation to prevent repeated-record leakage.
- Methane concentration and AUC measures are treated as sensor-derived proxies unless calibrated against methane mass flux.
- Repeatability and heritability are distinct; genetic parameters require pedigree/genomic relationship information and an appropriate model.
- CBBP/non-CBBP comparisons are observational unless supported by a causal design and confounding control.
- Clustering is exploratory; clusters are not assumed to represent validated biological types.
- Cross-species comparability requires species- and protocol-specific phenotype definitions and validation.

### Current prototype status
**Implemented in this prototype:** CSV/Excel ingestion, basic data validation, descriptive summaries, missingness/distribution/correlation visualisation, OLS/GEE/mixed-effects model interfaces, grouped ML regression benchmark, animal-level PCA and K-means diagnostics, and sheep-notebook phenotype derivations.

**Visible but not yet fully implemented:** several advanced analysis pages are scaffolds for the next development phase. The complete 29-part notebook workflow has not yet been fully ported or validated.

**Not yet production-ready:** institutional authentication, role-based access, persistent project storage, multi-tenant data isolation, background jobs, audit logging, backups, security hardening and deployment monitoring.

### Decisions requested from supervisor
1. Confirm priority livestock species and measurement protocols for the first validated release.
2. Confirm the primary methane phenotype(s) and biological interpretation to prioritise.
3. Agree the minimum validation design (repeat rounds, reference methane measurement, animal counts and metadata).
4. Review the proposed analytical modules and identify essential additions or exclusions.
5. Agree hosting, user roles, data governance and institutional access requirements.

### Recommended next phase
Validate the sheep workflow against the source notebook and empirical dataset; implement and unit-test the remaining analytical methods; then develop species-specific adapters and a secure multi-user deployment.
