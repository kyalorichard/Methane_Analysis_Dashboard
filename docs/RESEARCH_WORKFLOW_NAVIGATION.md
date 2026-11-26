# Research workflow navigation

The primary Streamlit navigation follows eight stages. Each page has one primary navigation location; legacy/specialist pages remain available under the stage where their methods belong.

| Stage | Primary purpose | Pages |
|---|---|---|
| 1. Research workspace | Projects, datasets, research overview, readiness, guided workflow, integrated analysis and run history | Home, 00, 22, 23, 26, 28 |
| 2. Data preparation | Import, QC, variable mapping, species/protocol setup and phenotype construction | 01, 16, 19, 24 |
| 3. Phenotype discovery | Descriptive summaries, distributions, phenotype exploration, group comparisons and PCA/clustering | 02, 05, 06, 08 |
| 4. Statistical inference | Conventional and mixed models, reliability/agreement, phenotype validation, allometry and equivalence | 03, 13, 21, 31, 33 |
| 5. Machine learning | Benchmarking, nested/grouped validation, research models and explainability | 04, 09, 25, 34 |
| 6. Longitudinal and emitter analysis | Repeated-round trajectories, emitter groups, persistence and transitions | 10, 18, 20 |
| 7. Advanced research | Sensitivity, forecasting, advanced methods, harmonisation/meta-analysis, research integration and configuration | 07, 11, 12, 17, 30, 32, 35, 36, 37 |
| 8. Scientific reporting | Publication suite, reproducibility exports, phenotype evidence scorecard and analysis comparison | 14, 15, 27, 29 |

## Navigation and ownership rules

- The sidebar contains exactly the eight workflow sections above.
- Every Streamlit page is linked once in the primary navigation; the home page is the entry point for the workspace.
- Reliability and measurement agreement are reached through page 33. Page 07 remains a specialist trajectory view and is labelled as legacy/supplementary.
- The page 32 integration lab and page 17 workbench remain available for specialist methods, but are not presented as the routine entry point for core workflows.
- The landing page exposes the same eight stages as quick links, so the first-run experience and sidebar use the same information architecture.
- Existing page implementations and analysis services are retained; this change reorganizes navigation and entry points, not the underlying statistical estimands or modelling algorithms.

## Validation

`tests/test_navigation_structure.py` checks the eight section labels, verifies that every page appears exactly once in the primary navigation, and checks that the reliability and integration pages render the shared sidebar.
