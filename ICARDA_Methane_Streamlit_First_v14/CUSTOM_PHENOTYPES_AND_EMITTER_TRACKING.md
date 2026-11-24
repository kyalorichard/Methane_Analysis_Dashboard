# Custom phenotype builder and longitudinal emitter tracking

## Custom phenotype builder
The **Custom Phenotype Builder** page lets users define new numeric variables from active dataset columns. It evaluates formulas using a restricted AST interpreter; it does not use Python `eval` or execute arbitrary code. Supported operators are `+`, `-`, `*`, `/`, `**`, `%`, unary signs, comparisons and logical operators. Supported functions are `abs`, `sqrt`, `log`, `log1p`, `exp`, `minimum`, `maximum`, `clip` and `where`.

Examples:
- `AUC_full / full_duration_sec`
- `(n_eruct / full_duration_sec) * 60`
- `log1p(mean_methane)`
- `clip(AUC_per_sec, 0, 100)`
- `where(weight > 0, mean_methane / weight, 0)`

New variables are added to the active in-session dataset and become available to phenotype analysis, ML benchmarking, variable importance, emitter cohorting and other pages. Definitions can be exported as JSON. The active derived data and definitions are session-scoped; export the derived dataset and registry to preserve them.

Users must verify unit consistency, biological validity, denominator handling and the intended phenotype construct. Formulas should be documented and reviewed before publication.

## Longitudinal emitter tracking
The **Longitudinal Emitter Tracking** page aggregates repeated records per animal and round (median or mean), classifies animals into low, intermediate and high groups independently within each round, and reports round-specific thresholds, transitions and persistence.

The tail percentage is 1–25% per tail. Classification is relative to the distribution in each round. Persistent high/low status is descriptive rank persistence, not heritability or absolute emission stability. Interpret alongside repeatability/ICC and mixed-effects analyses.

## Phenotype discovery and validation workbench (v9)

The new **Phenotype discovery & validation** page (`21_Phenotype_Validation.py`) provides structured exploratory review of source and custom phenotypes:

- completeness, descriptive distribution, skewness/kurtosis, coefficient of variation and descriptive IQR outlier flags;
- subgroup summaries (e.g., breed and sex);
- animal-level repeated-measure counts and exploratory one-way ICC, plus round summaries and paired-session change/correlation;
- Pearson and Spearman associations with continuous covariates, optionally after median aggregation per animal;
- a review checklist and JSON evidence report.

This page does not automatically certify a phenotype. The team must define the biological construct, protocol, calibration, dimensional units and meaningful thresholds. The ICC routine is an exploratory one-way approximation; fixed-session/repeated-measures designs may require a two-way mixed-effects or mixed model, and confidence intervals should be added before publication. Associations are descriptive and do not adjust for confounding. Predictive utility still requires animal-grouped validation, temporal/external validation and leakage controls.
