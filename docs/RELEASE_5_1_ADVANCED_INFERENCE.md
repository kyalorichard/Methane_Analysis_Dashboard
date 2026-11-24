# Release 5.1 — Advanced Inference and Scaling

Release 5.1 extends the integrated Release 5.0 research edition with three additional inference workflows in `pages/31_Advanced_Inference.py`.

## Added methods

### Conditional quantile regression
- Fits statsmodels `QuantReg` models at a selected quantile from 0.05 to 0.95.
- Supports numeric and categorical predictors.
- Reports coefficient estimates and the model summary.
- Estimates conditional quantiles, not conditional means. Standard errors are asymptotic; convergence, sparse factor levels, sample size and model specification require review.

### Allometric scaling
- Fits a log-log linear relationship for positive paired measurements.
- Reports the estimated scaling exponent, HC3 confidence interval, R-squared and model summary.
- Excludes non-positive observations because logarithms are undefined for them.
- The exponent is a statistical scaling relationship, not automatically an efficiency trait, causal effect or universal biological constant.

### Animal-level cluster bootstrap contrast
- Aggregates repeated records to one mean per animal and comparison group.
- Resamples animals within each of two selected groups to estimate a percentile confidence interval for the difference in animal-level means.
- Exposes bootstrap replicate count and a fixed seed for reproducibility.
- Does not adjust for confounding, herd/site clustering, unequal sampling mechanisms or covariates. If animals are nested in herds/sites, resampling may need to occur at the highest independent sampling unit.

## Validation

- Python compilation completed successfully.
- Test suite excluding Parquet-dependent tests: 51 passed.
- The Parquet tests require `pyarrow`, which is declared in `requirements.txt`; rerun the full test suite after installing project requirements.
- Streamlit browser interaction has not been end-to-end tested in this build environment.

## Use

Run `python -m pip install -r requirements.txt`, then `python -m streamlit run app.py`. Open **Advanced inference & scaling** from the sidebar.
