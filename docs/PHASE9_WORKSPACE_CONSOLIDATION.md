# Phase 9 — Research workspace and page-level consolidation

**Release:** 27 November 2026  
**Base:** Phase 8 Analytical Consolidation

## Changes

1. Promoted the existing advanced ML page to the **Unified Research Model Lab** entry point and added direct routes to regression benchmarking, classification/mixed-effects workflows, and variable importance.
2. Added a cross-link from Reliability & Agreement to the retained within-animal trajectory view. The trajectory page remains separate because it is a visual longitudinal exploration workflow, not an ICC or agreement estimator.
3. Added a cross-link from Scientific Publication & Reporting to quick data dictionary and run-manifest exports.
4. Connected static low/high emitter cohort assessment with longitudinal emitter persistence tracking. These remain distinct because their observational units and estimands differ.
5. Removed a duplicate `fit_allometry` key from the shared service registry.
6. Added a reusable `render_workflow_shortcuts` UI helper for consistent navigation between canonical workspaces and specialist workflows.

## Compatibility and scope

- No specialist page files were deleted or renamed; existing page URLs remain available.
- No statistical estimands or model-validation designs were collapsed.
- This release consolidates workspace entry points and navigation, not every page's underlying UI implementation. Full code-level page extraction remains a subsequent migration requiring feature-parity tests.

## Validation

- Python syntax compilation and static page-link target checks are run as part of this release.
- Streamlit browser, authentication, PostgreSQL, S3 and production deployment smoke tests are not performed in this local package build.
