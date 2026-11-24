# Low- and high-emitter reporting

The new **Low & High Emitter Assessment** page defines relative phenotype cohorts using a user-selected percentile in each tail.

## How it works
1. Select a numeric phenotype (for example `mean_methane`, `AUC_per_sec`, or another validated phenotype).
2. Select the percentage for each tail (1–25%). A 10% setting selects approximately the bottom 10% as low emitters and top 10% as high emitters.
3. If an animal identifier is available, repeated records are first aggregated to one animal-level value using the selected median (default) or mean.
4. A minimum number of records per animal can be required.
5. The page displays the cohort sizes, phenotype cut-points, distribution, phenotype summary, numeric profiles, categorical composition and unit-level assignments.
6. Export the assignments as CSV or the complete report as a multi-sheet Excel workbook.

## Statistical interpretation
- Cohorts are relative to the selected analysis dataset and phenotype; they are not universal biological categories.
- Percentile ranks are used to keep group sizes close to the requested proportion. When tied values occur at a boundary, tied observations can be split by rank order. Quantile cut-points are shown transparently.
- The default animal-level aggregation avoids treating repeated measurements from the same animal as independent animals.
- If AnimalID is unavailable, the page falls back to record-level analysis and displays a warning.
- For species, breed, sex, round or protocol-specific comparisons, define the target analysis subset before generating the cohorts. Avoid pooling biologically distinct species or non-comparable protocols without justification.
- AUC and concentration-derived proxies are not methane mass flux unless the instrument and protocol have been calibrated accordingly.

## Outputs
- `low_high_emitter_assignments.csv`
- `low_high_emitter_report.xlsx` containing cohort summary, numeric profiles, categorical profiles, assignments and configuration.
