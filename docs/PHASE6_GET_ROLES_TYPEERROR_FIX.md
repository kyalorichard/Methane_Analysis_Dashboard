# Phase 6 hotfix: Scientific Analysis Workbench TypeError

## Symptom
The Streamlit page `pages/17_Scientific_Analysis_Workbench.py` failed at startup on the line assigning `roles=get_roles()`.

## Cause
The shared helper in `analysis_engine/ui.py` is defined as `get_roles(df)` and requires the active DataFrame as its positional argument. The workbench called it without that required argument.

## Fix
The page already obtains the active dataset using `df=get_data().copy()`. The call now passes that DataFrame: `roles=get_roles(df)`.

## Validation
- Python compilation passed for the corrected page and shared UI module.
- Applicable automated test suite: 176 passed.
- 64 warnings remain, including resource and statsmodels convergence warnings; these are not failures and should be reviewed separately.
- Two PyArrow-dependent dataset-format tests were excluded because PyArrow was unavailable in the build environment.
- Live Streamlit browser and production cloud deployment tests were not performed.
