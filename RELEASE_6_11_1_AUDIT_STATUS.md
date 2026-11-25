# End-to-End Audit Status — Release 6.11.1

## Verified in source and automated tests
- 38 Streamlit page scripts are present.
- The storage facade is used by shared navigation and the Species & Protocol Configuration page; the landing page no longer imports the cloud workspace module directly.
- Authenticated subject is used to scope centrally loaded settings when a principal is present in session state.
- Project changes invalidate stale active dataset and selected analysis result state.
- Several core analytical pages consume settings for defaults or interpretation.
- Settings validation has additional range checks.
- Python compilation passed.
- 106 tests passed when the Parquet test module was excluded.

## Known issues / incomplete work
1. Two Parquet tests remain unexecuted successfully in this environment because `pyarrow` is absent. It is declared in `requirements.txt`; rerun those tests after dependency installation.
2. Settings are not yet consumed by every analytical page or every model engine. The Settings UI currently exposes some parameters that remain informational/configuration-only until integrated into their corresponding engines.
3. The project workspace DB, analysis settings/experiment DB, and analysis run DB remain separate by default. `METHANE_METADATA_DB` permits an opt-in shared path for settings/experiments and run metadata, but existing data migration is not automated.
4. Several pages provide related but not identical workflows. No specialist page was deleted in this release; consolidation of UI workflows requires a separate user-facing navigation redesign and functional equivalence review.
5. No live Streamlit browser test, Streamlit Cloud deployment test, cloud PostgreSQL/S3 test, Entra identity test, or persistence-after-restart test was possible in this environment.
6. Mixed-effects and ARIMA/SARIMA tests emit convergence warnings. These are not automatically fatal, but model convergence and diagnostics must be checked on actual study data.
7. Local filesystem storage is suitable only when the host provides persistent storage and appropriate access controls. It is not a substitute for multi-tenant cloud storage in a horizontally scaled deployment.

## Production acceptance checklist
- [ ] Install all dependencies from `requirements.txt`, including `pyarrow`.
- [ ] Run the complete test suite without exclusions.
- [ ] Test fresh database creation and upgrade from an existing Release 6.10.1 workspace.
- [ ] Test user isolation and project-level access for at least two users and two tenants.
- [ ] Test switching projects and datasets without stale data/results.
- [ ] Test save/reload of settings for each species and project.
- [ ] Verify every Settings parameter is either applied by an engine or clearly marked as not currently applied.
- [ ] Verify repeated-measure grouped validation and temporal validation on representative datasets.
- [ ] Test all 38 pages in a browser at desktop and mobile widths.
- [ ] Test cloud PostgreSQL/S3 and persistent local deployment separately.
- [ ] Test restart persistence and backup/restore.
- [ ] Review statistical model convergence and forecast residual diagnostics on representative study data.
