# Release 6.15.1 — Longitudinal paired-round hotfix

## Issue addressed
The Longitudinal Analysis page could raise a pandas `ValueError` when the baseline and comparison round selectors held the same value. Selecting the same pivot column twice creates duplicate labels; indexing that duplicated label returns a DataFrame, which cannot be assigned to a single `change` column.

## Changes
- The comparison-round selector now excludes the selected baseline round.
- A stale Streamlit comparison selection is reset when it equals the baseline or is no longer valid.
- Paired calculations use a shared helper that constructs explicitly named baseline, comparison, and change Series.
- Non-numeric measurements are coerced to missing values; incomplete animal pairs are excluded.
- Empty complete-pair results and ambiguous round labels produce explanatory messages rather than an unhandled exception.
- Added regression tests for normal change calculation, same-round selection, duplicate labels, and non-numeric/incomplete pairs.

## Verification
- Python compilation: passed for the modified page and helper.
- Focused longitudinal tests: 4 passed.
- Project tests (excluding `tests/test_dataset_formats.py`): 127 passed, 9 warnings.
- The excluded dataset-format tests require `pyarrow`, which is not installed in this verification environment.
- Streamlit Cloud/browser and production database/object-storage integration were not exercised here.
