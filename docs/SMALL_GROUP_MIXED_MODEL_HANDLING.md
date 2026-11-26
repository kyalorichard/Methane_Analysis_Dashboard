# Small-group mixed-effects model handling

The random-intercept model no longer hard-stops solely because fewer than five animals/groups are available. It will attempt estimation when at least two independent groups contribute and at least two groups have repeated observations. Fits with fewer than five groups are explicitly flagged as exploratory because variance components and inferential statistics may be unstable.

This is not a guarantee that a small-sample mixed model is estimable or scientifically adequate. Convergence, singular/boundary variance estimates, residual diagnostics, group balance, and the study design must still be reviewed. If fewer than two groups have repeated observations, the application directs the analyst toward a fixed-effects or descriptive alternative rather than presenting an unsupported random-intercept estimate.
