# UI/UX redesign — v10

## Design direction
- ICARDA-inspired research workspace using forest green, warm gold, white surfaces and muted neutral backgrounds.
- Consistent typography, spacing, rounded panels, restrained shadows and responsive layouts.
- Shared page header, metric cards, chart surfaces, data tables, form controls and alert styling.

## Navigation and onboarding
- Sidebar brand lockup and clearer data-workspace section.
- More explicit dataset import guidance and active-dataset status.
- Landing page reorganised into a three-step onboarding sequence and a recommended scientific workflow.
- Clearer research-principle reminders for animal-grouped validation, phenotype documentation and methane-signal interpretation.

## Compatibility
- Existing analytical pages and analysis functions retained.
- Existing `header()` and `metric_row()` helpers remain the shared page-level components.
- CSS is responsive for narrower screens and uses graceful system-font fallbacks.
- No new Python package dependencies.

## Validation
- Python compilation: passed.
- Automated tests: 25 passed.
- One pre-existing benign warning remains in a formula-builder test (`sqrt` on a negative test value).
- This release has not been visually browser-tested on every screen size. Review with the local Streamlit app before institutional deployment.
