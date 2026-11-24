# Release 6.7 — Analysis and Model Settings

## Summary
Adds a central Streamlit settings page at `pages/36_Analysis_Model_Settings.py`. Settings include grouped-CV folds, cluster-bootstrap replicates, random seed, numeric/categorical imputation choices, numeric scaling, and model hyperparameters for Random Forest, Extra Trees, HistGradientBoosting, SVR and KNN. Settings can be exported/imported as JSON and reset to defaults.

## Integration
The matched conventional-statistics-versus-ML benchmark on page 34 reads saved model parameters and comparison defaults from `st.session_state.analysis_settings`. The settings are session-scoped; they are not persisted across browser sessions or users. Numeric and categorical imputation and numeric standardisation settings are applied by the page 34 comparison pipeline within each training fold.

## Scientific safeguards
- Hyperparameters are applied by estimator `set_params` and unknown parameters are ignored by the comparison engine.
- The same grouped folds and selected predictor set are retained across model families.
- Settings do not automatically tune hyperparameters; they set explicit user-specified values.
- This page configures the matched comparison only. Other pages have independent controls.

## Limitations
- GEE, mixed-effects, OLS, spline, quantile and allometric model parameters are not yet configurable here.
- JSON configuration import validates schema and sklearn parameter names; detailed domain/range validation remains delegated to scikit-learn at model fit time.
- Browser-based Streamlit end-to-end testing is not available in this build environment.
