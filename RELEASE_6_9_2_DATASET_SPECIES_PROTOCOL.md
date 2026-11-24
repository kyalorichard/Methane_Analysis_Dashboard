# Release 6.9.2 — Dataset-level Species & Protocol Configuration

## Summary
Species and measurement protocol configuration is now stored against an individual project dataset rather than only in the active Streamlit session. A project can therefore contain datasets with different species, variable mappings, instruments, units, calibration status and protocol references.

## Changes
- Reworked **Species & protocol configuration** to select a project and one of its stored datasets.
- Added dataset-scoped species selection and editable variable-role mappings.
- Added dataset-scoped measurement metadata: instrument, method, methane units, calibration status, SOP/protocol reference and minimum recording duration.
- Persisted the configuration in the dataset's existing `protocol_json` metadata field for both local SQLite and cloud PostgreSQL backends; no new database migration is required.
- Added backward-compatible reading of protocol metadata saved by earlier releases.
- Restoring a stored dataset in Project Workspace now restores its saved species, variable mapping and measurement protocol into the analysis session.
- Added configuration version metadata and timestamp in local mode.

## Important behaviour
- Configuration is saved only for datasets already stored in a project. Session-only uploads must first be saved to a project.
- Variable mapping and protocol metadata are configuration/provenance; they do not automatically validate instrument calibration or establish a physical methane flux.
- Concentration and AUC remain sensor-derived signal phenotypes unless validated calibration supports conversion to a mass-flux unit.
- Species profiles currently provide alias-based role inference and basic checks. This release does not introduce species-specific biological reference ranges or instrument calibration equations.

## Verification
- Python compile check passed for the modified configuration page, project workspace page and storage modules.
- Local SQLite test passed for dataset-level configuration save/load, legacy protocol metadata compatibility and species update.
- Full Streamlit browser workflow and deployed cloud backend were not exercised in this package build.
