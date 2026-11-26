# Research Diagnostics & Methods

This page is an advanced, cross-cutting workbench. It is not a separate software release and its user-facing name must not include release numbers.

## Included capabilities

1. **Dataset integrity and quality checks** — reports row/column counts, exact duplicate rows, missing cells, fully empty rows, duplicate/blank column names and non-finite numeric values. This is a structural screening report, not a complete scientific QC protocol: it does not establish unit correctness, biological plausibility, instrument calibration or protocol compliance.
2. **Longitudinal mixed-effects modelling** — fits a Gaussian mixed model with fixed time effects and correlated group-level random intercepts and time slopes. It requires at least eight independent groups as a practical minimum and at least two time points within each retained group. Convergence, singularity, residuals, time coding and the sampling hierarchy still require review.
3. **Consensus clustering** — repeatedly subsamples animal-level profiles, applies scaled K-means and calculates a co-association matrix. It is exploratory; cluster count, feature selection, missing-data handling and stability should be sensitivity-tested before biological interpretation.
4. **Reproducibility and provenance manifest** — exports a JSON manifest with a dataset fingerprint, dataset dimensions, analysis name, supplied parameters, random seed and selected software versions. It does not embed raw data or prove measurement validity, protocol compliance or independent validation.

## Placement in the research workflow

This page remains under **Advanced Research** as a specialist workbench. The routine entry points should remain in their corresponding workflow stages: structural data QC in Data Preparation, ordinary phenotype clustering in Phenotype Discovery, standard mixed models in Statistical Inference, and publication-ready provenance exports in Scientific Reporting. Avoid adding a second primary entry point for those routine workflows.

## Naming convention

- User-facing page title: **Research Diagnostics & Methods**.
- Sidebar label: **Research diagnostics & methods**.
- Implementation module: `analysis_engine.research_methods`.
- Former `analysis_engine.release6` import remains as a compatibility shim only; new code should not import it.
- Product UI must not display historical release identifiers as module names or badges. Historical changelog entries may retain release labels for traceability.
