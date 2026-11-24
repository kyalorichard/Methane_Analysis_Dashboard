# Release 6.5.0 — Multi-study harmonisation and meta-analysis

Adds an explicit study harmonisation workflow, protocol comparability audit and DerSimonian–Laird random-effects meta-analysis. See `docs/RELEASE_6_5_MULTI_STUDY_HARMONISATION.md`.

Validation in the build environment: 76 tests passed when excluding the Parquet-format test module. The complete suite reports 78 passed and 2 failures because `pyarrow` is not installed in the build environment. Python compileall passed. Six pre-existing runtime/statistical warnings remain. Browser end-to-end testing was not performed.
