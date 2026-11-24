# Release 6.3 — Classification validation and external assessment

## Scope

Release 6.3 closes part of the Release 6.2 classification-validation gap by adding a nested, group-aware classification workflow with out-of-fold probability outputs and an optional cross-fitted sigmoid calibration map. It also exposes frozen-model external classification validation from the Advanced ML & Explainability page.

## Methods

- **Outer evaluation:** `StratifiedGroupKFold`; every record from a selected independent group remains in one outer fold.
- **Hyperparameter selection:** optional `GridSearchCV` is restricted to each outer training partition and uses group-disjoint inner folds.
- **Probability calibration:** sigmoid calibration is fitted using inner out-of-fold probabilities generated within each outer training partition. Outer test observations are not used to fit the calibration map.
- **Metrics:** accuracy, balanced accuracy, macro/weighted F1, macro precision/recall, ROC-AUC (binary or multiclass OVR), log loss and multiclass Brier score. OOF class probabilities and confusion matrices are downloadable.
- **External classification:** a development-cohort model is fitted once and evaluated on an uploaded external cohort without refitting. Required features and class definitions must be harmonised.

## Scientific limitations

1. Group labels must represent the highest independent sampling unit. If animals are nested within herds/farms/sites, grouping only by animal may still overstate transportability.
2. Stratified grouped folds require sufficient independent groups and representation of every class in each training partition. Sparse classes may cause incomplete folds; the workflow reports these rather than silently filling missing predictions.
3. The current calibration map is sigmoid/logistic calibration on log probabilities. Isotonic calibration, calibration method selection and decision-threshold optimisation are not yet implemented.
4. Calibration and discrimination metrics are computed from pooled OOF predictions. Fold-level uncertainty intervals and decision-curve analysis remain pending.
5. External validation is meaningful only when the cohort is genuinely independent, outcome labels are harmonised, and predictor measurement protocols and units are comparable.
6. External classification currently requires the external cohort to contain only classes represented by the fitted development classifier.
7. Classification-specific SHAP, subgroup calibration and temporal/geographic domain-shift analysis remain pending.

## Validation

The release adds tests for nested group-disjoint classification, OOF probability completeness and normalisation, too-few-group safeguards, and frozen-model external classification. Run `python -m pytest -q tests/test_classification_validation.py` for focused tests and `python -m pytest -q` for the complete suite.
