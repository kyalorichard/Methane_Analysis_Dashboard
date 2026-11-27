# Phase 11 — Unified Research Model Lab workflow consolidation

## Purpose
Organise the existing advanced predictive modelling capabilities into three research workflows while preserving their analytical implementations and page routes.

## Workspace structure
The Unified Research Model Lab now presents three tabs sharing one analysis configuration (dataset, continuous target, grouping unit, random seed and predictors):

1. **Regression & phenotype prediction** — grouped learning curves, group-split conformal prediction intervals and independent external regression validation.
2. **Classification & phenotype identification** — grouped classification benchmarking, nested grouped classification with optional tuning and sigmoid calibration, and independent external classification validation.
3. **Model validation & interpretation** — group-bootstrap feature-selection stability, SHAP explainability, links to conventional-vs-ML comparison, and external-cohort transportability audit.

## Methodological safeguards retained
- Internal validation keeps observations from the same selected group together.
- The user is advised to select the highest independent sampling unit (e.g. herd/farm/site) when animals are clustered above animal level.
- Predictors should be available at the intended prediction time and must not be derived from the outcome.
- Feature importance and SHAP describe model reliance, not causal effects.
- Conformal coverage depends on exchangeability at the independent-group level.
- External validation requires an independent cohort with harmonised variables, units and measurement protocol.

## Compatibility
The existing specialist pages and routes are retained. Phase 11 reorganises the Model Lab interface; it does not delete or physically merge the separate Statistical Models, ML Benchmarking, Explainability or Conventional vs ML Comparison pages.

## Validation
- Python compilation: passed.
- Test suite excluding `tests/test_dataset_formats.py`: 196 passed, 9 warnings.
- Dataset-format tests were excluded because PyArrow is not installed in the validation environment; the project requirements include PyArrow.
- Streamlit browser interaction, cloud deployment, and live database/storage integrations were not tested.
