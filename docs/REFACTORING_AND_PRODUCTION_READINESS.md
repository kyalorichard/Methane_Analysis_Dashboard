# Methane Phenotype Analytics — Refactoring and Release Notes

## Release objective

This update reduces duplicated scientific computation, simplifies the primary navigation, improves the landing dashboard, and strengthens source-data provenance. It is a backwards-compatible refactor: historical module entry points remain available as thin adapters where other pages or tests depend on them.

## Canonical analytical ownership

| Capability | Canonical owner | Compatibility entry points |
|---|---|---|
| Subject × occasion panel construction | `analysis_engine.reliability.build_subject_occasion_panel` | Pages 07 and 33 now call the service registry |
| Balanced-panel ICC(1)/ICC(2)/ICC(3) | `analysis_engine.reliability.estimate_balanced_panel_icc` | `release6.estimate_repeatability_icc` |
| Unbalanced long-format ICC(1,1) | `analysis_engine.reliability.estimate_long_format_icc1` | `advanced.repeatability_icc`, phenotype validation |
| Subject-cluster ICC bootstrap | `analysis_engine.reliability.bootstrap_long_format_icc1` | `advanced.bootstrap_icc` |
| Paired Bland–Altman statistics | `analysis_engine.reliability.bland_altman_paired` | `release6.bland_altman_summary` |
| Long-format occasion pairing | `analysis_engine.reliability.bland_altman_long_format` | `advanced.bland_altman` |
| Within/between-subject variance decomposition | `analysis_engine.reliability.within_between_variability` | `release6.within_between_variability` |
| Group comparison test | `analysis_engine.advanced.group_comparison` | service registry, Group Comparisons and Integrated Analysis |
| Quantile regression | `analysis_engine.advanced.fit_quantile_regression` | `advanced_research.fit_quantile_regression` adapter |

### Methodological distinctions deliberately retained

- Balanced-panel two-way ICCs and unbalanced long-format one-way ICC(1,1) are not interchangeable estimands. They share a module, but remain separate explicitly named functions.
- Covariate-adjusted allometry (`advanced.fit_allometry`) and simple two-variable allometric scaling (`advanced_research.fit_allometric_scaling`) serve different model specifications and are not collapsed.
- Group comparison tests are not substitutes for mixed-effects inference when repeated measures, covariates, herd/site clustering or complex sampling must be modelled.

## Interface and navigation changes

- Primary navigation is now workflow-led and presents one canonical route for reliability/agreement.
- Older or overlapping workbenches remain accessible under **Advanced / Compatibility Pages** rather than being deleted.
- Page 07 remains for within-animal trajectories; its hand-coded ICC calculation has been removed. Formal repeatability is routed to Page 33.
- Page 08 now uses the shared group-comparison service and defaults to animal-level aggregation when an animal identifier is available. Animals assigned to multiple groups are flagged and excluded from that comparison rather than silently assigned.
- The landing page surfaces study structure, repeated-animal counts, duplicate rows, non-finite numeric cells and recommended next actions.

## Source-data provenance

New project dataset uploads retain two separate immutable objects:

1. The exact original uploaded bytes, with source SHA-256.
2. A canonical Snappy-compressed Parquet derivative, with its own SHA-256.

The local backend stores both under the project workspace. The cloud backend stores both as separate KMS-encrypted S3 objects and records the original object key in `datasets.source_storage_key`. The original upload can be downloaded from the project workspace after authorization and checksum verification. Legacy datasets without an original-source object remain readable; the UI identifies that limitation.

Database migration: `database/migrations/004_original_source_storage.sql`.

## Validation

Run:

```bash
python -m pip install -r requirements.txt
python -m compileall -q .
pytest -q
```

The review container did not have `pyarrow` installed, so Parquet upload tests cannot pass there until dependencies are installed. The project requirements already declare `pyarrow`. Mixed-effects convergence warnings are not suppressed; inspect optimizer status, singularity and Hessian diagnostics before reporting those fits.

## Remaining production gates

This release does not certify a production deployment. Before institutional deployment:

- Apply the database migration to the target PostgreSQL database and verify rollback/backup procedures.
- Configure S3 bucket policy, KMS key policy, lifecycle/retention, versioning and access logging for both source and Parquet objects.
- Verify tenant isolation and project read/write permissions with integration tests against PostgreSQL and S3.
- Complete Celery task execution and result persistence; the current worker scaffold is not a full asynchronous analysis service.
- Complete the FastAPI analysis-run authorization and persistence path.
- Validate the scientific calculations against the study's original reference notebook/protocol and an independent dataset.
- Test the rendered Streamlit app in the intended browser and deployment environment.

No statistical result should be treated as biological validation solely because a computation completed successfully.
