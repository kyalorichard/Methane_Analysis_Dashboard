"""Shared helpers for animal-level longitudinal comparisons."""

import pandas as pd


def paired_round_changes(pivot: pd.DataFrame, baseline, comparison) -> pd.DataFrame:
    """Return complete animal-level pairs and comparison-minus-baseline change.

    The function deliberately constructs the output from Series rather than
    ``pivot[[baseline, comparison]]`` so duplicate selections can never create
    duplicate output columns. Round labels must identify exactly one column.
    """
    if baseline == comparison:
        raise ValueError("Choose two different monitoring rounds for a paired comparison.")

    positions = {}
    for label in (baseline, comparison):
        matches = [i for i, value in enumerate(pivot.columns) if value == label]
        if len(matches) != 1:
            raise ValueError(
                f"Monitoring round {label!r} must identify exactly one pivot column; "
                f"found {len(matches)}. Check the round labels in the source data."
            )
        positions[label] = matches[0]

    baseline_values = pd.to_numeric(pivot.iloc[:, positions[baseline]], errors="coerce")
    comparison_values = pd.to_numeric(pivot.iloc[:, positions[comparison]], errors="coerce")
    paired = pd.DataFrame(
        {
            "baseline_value": baseline_values,
            "comparison_value": comparison_values,
        },
        index=pivot.index,
    ).dropna(subset=["baseline_value", "comparison_value"])
    paired["change"] = paired["comparison_value"] - paired["baseline_value"]
    return paired
