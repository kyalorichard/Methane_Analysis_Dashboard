# Phase 10 slider hotfix — 2026-11-27

## Issue
`StreamlitInvalidMinMaxError` occurred on the animal-grouped CV folds slider when the active dataset had fewer than four independent groups. In that case the slider could be rendered with equal minimum and maximum values (`3` and `3`), which Streamlit rejects.

## Fix
- Render the fold slider only when at least five independent groups are available (the page's existing minimum for enabling a comparison run).
- Bound the slider maximum to `min(8, n_groups)` and clamp the configured default into the valid range.
- For fewer than five groups, set the internal fallback to three folds and show an explanatory caption; the comparison run remains disabled by the existing group-count guard.

## Validation
- Python syntax compilation passed.
- The slider bounds are strictly ordered whenever the slider is rendered.
- The low-group branch does not instantiate a slider.
- Full Streamlit Cloud deployment/browser validation remains the user's deployment environment responsibility.
