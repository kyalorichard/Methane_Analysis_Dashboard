# Release 6.1 — Reliability, Repeatability and Measurement Agreement

Release 6.1 extends the consolidated Release 6.0 platform with explicit subject-level reliability and paired-method agreement workflows.

## Added capabilities

- ICC(1), ICC(2) and ICC(3) single-measure estimates from balanced subject-by-occasion panels.
- Corresponding average-measure ICC estimates.
- Subject-level nonparametric bootstrap confidence intervals for single-measure ICC.
- Balanced-panel method-of-moments between- and within-subject variance decomposition.
- Bland–Altman bias and 95% limits of agreement, with subject-pair bootstrap intervals for bias and limits.
- Streamlit page `33_Reliability_and_Agreement.py` with analysis summaries, diagnostics visualisation and JSON exports.

## Statistical design and interpretation

- ICC(1) uses a one-way random-effects formulation.
- ICC(2) uses a two-way random-effects absolute-agreement formulation.
- ICC(3) uses a two-way mixed-effects consistency formulation.
- Subjects are rows and occasions/methods are columns. The ICC calculation uses complete-case rows; report the number excluded and assess whether missingness could be informative.
- Bootstrap resampling is at the subject/pair level. If animals are clustered within herds, farms or sites, the independent resampling unit may need to be the higher-level cluster.
- The within-subject variance component includes occasion effects and residual variation; it is not necessarily pure instrument error.
- ICC is population- and design-dependent and is not heritability.
- Bland–Altman limits are bias ±1.96 SD of paired differences. Agreement requires prespecified acceptable limits and graphical assessment for proportional bias and heteroscedasticity. Correlation is not agreement.

## Validation

New synthetic tests cover high-repeatability panels, systematic occasion shifts (absolute agreement versus consistency), Bland–Altman bias and limits, and complete-case handling. Run the full test suite after installing all requirements, including `pyarrow` for Parquet tests.

## Remaining roadmap items

This release does not claim to complete nonlinear mixed-effects models, genomic association, full SHAP integration, a dataset-grounded AI assistant, full multi-tenant production recovery, or deployment security verification.
