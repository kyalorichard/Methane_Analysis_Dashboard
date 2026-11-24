# Prototype status — updated interactive dashboard

This is a local, single-user Streamlit research prototype with 15 interactive modules. It includes dataset upload, variable mapping, QC, descriptive analysis, conventional model fitting, animal-grouped ML benchmarking, animal-level PCA/clustering, candidate phenotype summaries, exploratory repeatability, group comparisons, held-out permutation importance, longitudinal summaries, allometric regression, duration sensitivity, an explicit-margin equivalence workflow, an evidence scorecard and reproducibility exports.

## Important limitations
- This is **not production multi-user software**: no authentication, tenant isolation, database-backed project persistence, object storage, background job queue, audit trail or deployment monitoring is implemented.
- Several modules provide exploratory or unadjusted analyses. In particular, repeatability uses a simple balanced complete-case ICC estimate; group comparison tests are record-level and unadjusted; equivalence is independent-sample Welch TOST logic. Use model-based methods for repeated animal observations before publication.
- Machine-learning benchmarking uses GroupKFold by animal, but does not yet provide nested hyperparameter optimization or external validation.
- Species selection is a workspace label. Species-specific phenotype adapters and protocol harmonisation must be configured before multi-species comparison.
- Methane concentration and sensor-derived AUC are not methane mass flux unless a validated calibration model is applied.

## Run locally
1. Create and activate a Python virtual environment.
2. `python -m pip install -r requirements.txt`
3. `streamlit run app.py`
4. Use the sidebar to load the included ICARDA sheep dataset or upload another CSV/Excel file.
