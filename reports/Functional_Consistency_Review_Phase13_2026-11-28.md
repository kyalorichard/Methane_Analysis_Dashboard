# Methane Phenotype Analytics — Functional Consistency & Duplication Review

**Review baseline:** Phase 12 — Versioned Model Registry  
**Review date:** 28 November 2026  
**Scope:** Streamlit navigation and page journeys, analytical service dispatch, related workflow overlap, source compilation, tests and exact-function duplication audit.

## Executive assessment

The dashboard has a broad and useful analytical feature set. The main usability risk is **competing entry points for the same research task**, rather than exact copy-and-paste function duplication. Older pages remained visible beside consolidated workspaces, so users could reasonably interpret them as separate or preferred workflows.

This review makes the canonical route explicit, groups related tasks, and keeps older URLs available without keeping duplicate analysis forms in the primary navigation. No scientifically distinct estimator was merged merely because it shares a domain label with another method.

## Changes made in this review

### 1. One navigation catalogue

- Added `analysis_engine/navigation.py` as the single source of truth for page navigation.
- Sidebar navigation now has eight primary workflow groups, in a consistent order:
  1. Research workspace
  2. Data preparation
  3. Phenotype discovery
  4. Statistical inference
  5. Machine learning
  6. Longitudinal & emitter analysis
  7. Advanced research
  8. Scientific reporting
- The data-preparation order is now import/mapping → species/protocol → preparation → QC → phenotype construction.
- Each destination is listed once. Older/specialist pages are separated into a closed-by-default specialist/legacy section.
- Added navigation tests that verify every page exists and is reachable exactly once across primary and specialist routes.

### 2. Model Lab consolidation

The Unified Research Model Lab (`pages/34_Advanced_ML_Explainability.py`) is now the canonical destination for:

- Standard animal-grouped regression benchmarking
- Nested animal-grouped regression validation
- Grouped learning curves
- Feature-selection stability
- SHAP explainability
- Group-split conformal prediction intervals
- Independent external regression validation
- Grouped classification and nested grouped classification
- External classification validation and model-registry workflows

The standard and nested regression interfaces were moved from the former standalone regression benchmark page into the Model Lab's regression workflow. Existing session-state result keys are retained for continuity where practical.

The former pages 04 and 25 now act as compatibility landing pages pointing to the canonical Model Lab and, for mixed-effects models, the Statistical Models page. This removes parallel forms while preserving old bookmarks and direct URLs.

### 3. Inference workbench consolidation

- The former broad Scientific Analysis Workbench (page 17) is now a focused route directory pointing to Reliability & Agreement, Group Comparisons, Advanced Inference, Sensitivity & Robustness, PCA/Clustering and Scientific Reporting.
- The former Advanced Analysis page (page 11) now points to the canonical Advanced Inference & Scaling workspace (page 31).
- The legacy workbench no longer hosts a second set of calculations that could drift from the dedicated pages.
- Page 09 remains a specialist route for held-out permutation importance. This is intentionally distinct from SHAP explanations and feature-selection stability; it is labelled as a specialist method rather than presented as a competing Model Lab.
- Page 07 remains available as a focused within-animal trajectory visualisation, distinct from formal ICC estimation in page 33.

### 4. Consistent cross-links and landing page

- The Model Lab now links to matched conventional-versus-ML comparison and the specialist permutation-importance workflow rather than sending users to three parallel legacy model pages.
- The home-page workflow cards now direct users to canonical Statistical Models and Unified Research Model Lab destinations.
- Specialist pages remain reachable, but their role is made explicit.

## Current functional ownership map

| Research task | Canonical destination | Related specialist/compatibility route | Boundary retained |
|---|---|---|---|
| Project lifecycle and analysis history | Project Workspace / Analysis History | Guided workflow, Integrated Analysis Centre | Lifecycle, guided orchestration and saved-run review are different user tasks |
| Import, protocol, preparation and QC | Data Import & Mapping; Species & Protocol; Preparation Studio; QC Centre | None | Each is a distinct ordered data-preparation stage |
| Descriptive phenotype discovery | Descriptive Analysis; Phenotype Analysis; Group Comparisons; PCA | Phenotype Scorecard | Descriptive, inferential group contrasts and unsupervised structure are not interchangeable |
| Conventional inference | Statistical Models; Advanced Inference | Legacy nonlinear page now routes to Advanced Inference | OLS, GEE, random-intercept/slope models, quantile and allometric models retain their assumptions |
| Repeatability and agreement | Reliability & Agreement | Within-animal trajectory view; Phenotype Validation | ICC designs and agreement estimands remain distinct; trajectory plotting is not an ICC estimator |
| Predictive modelling | Unified Research Model Lab | Former regression/classification pages route to canonical pages | Standard grouped CV, nested validation, external validation and explainability remain separate evaluation designs |
| Conventional-vs-ML comparison | Conventional vs ML Comparison | Linked from Model Lab and Statistical Models | Matched folds and common evaluation data are required for valid comparison |
| Longitudinal and emitter work | Longitudinal Analysis; Emitter Cohort; Emitter Tracking; Forecasting | None | Cohort assignment, round transitions, trajectory modelling and forecasting answer different questions |
| Advanced research | Advanced Research Analytics; Sensitivity; Harmonisation; Diagnostics; Settings | Legacy workbench routes to focused pages | Meta-analysis, sensitivity analysis and method diagnostics remain separate |
| Scientific outputs | Publication Suite; Analysis Comparison; Reports & Exports | None | Manuscript-ready outputs, run comparison and quick exports remain distinct |

## Duplication audit

- Exact AST duplicate function groups: **0**.
- Unique top-level function bodies in the scanned analytical and page code: **211**.
- This is a conservative exact-match test only. It does not prove scientific equivalence or absence of semantic overlap.
- The most important overlap was in page-level workflows and repeated UI entry points. This review addresses the clearest duplicated journeys without collapsing distinct scientific estimands.

## Remaining architectural risks / recommended next review

1. **Service boundary is not yet universal.** `analysis_engine/service_registry.py` is the preferred shared dispatch layer, but some pages still import analytical functions directly. Continue migrating shared calculations to named services and typed result contracts.
2. **Reliability versus phenotype validation.** Page 21 and page 33 both touch repeated-measure evidence. Keep the former focused on phenotype validation/readiness and the latter on formal reliability/agreement; add explicit cross-links and parity tests where they call the same estimator.
3. **Mixed-model API consistency.** Random-intercept, random-slope, GEE and population-average models have distinct estimands. Standardise inputs, result metadata, convergence warnings and diagnostics without forcing them into one estimator.
4. **QC state persistence.** QC decisions and some workflow state are session-scoped. Confirm which decisions should be persisted as project-level artifacts, and make their lineage explicit before users rely on them across sessions.
5. **Model registry durability.** Phase 12's local SQLite/filesystem registry remains unsuitable for durable multi-instance cloud deployment unless backed by persistent shared storage. This review does not change the Phase 12 storage limitation.
6. **Page 09 permutation importance.** It remains a separate specialist method because it is not interchangeable with SHAP. A future UX pass could bring it into the Model Lab as a dedicated tab after result and pipeline parity tests.

## Verification

- `python -m compileall -q .`: passed.
- `pytest -q --ignore=tests/test_dataset_formats.py`: **207 passed, 9 warnings**.
- The 9 warnings include pandas invalid-square-root handling in a fixture and statsmodels convergence / Hessian / boundary warnings in mixed-model and forecasting tests. They are retained as diagnostic caveats; test success does not imply those fitted models converged reliably.
- Exact duplicate function audit: **0 groups / 211 unique function bodies**.
- All 40 page files are reachable exactly once across the 8 primary workflow groups and the specialist/legacy group; `app.py` is also a primary route.
- Dataset-format tests were excluded because PyArrow is not available in this validation environment.
- No live Streamlit browser session, production database, external object store or cloud deployment smoke test was performed.

## Release note

This is a navigation and workflow-consolidation release. It retains the full page inventory and compatibility URLs, moves standard and nested grouped regression into the canonical Model Lab, and removes duplicate forms from selected older pages. It does not claim to complete a full migration of every analytical calculation into the service registry.
