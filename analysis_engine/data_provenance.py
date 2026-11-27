"""Canonical dataset provenance utilities shared across QC and research workflows."""
from __future__ import annotations
import hashlib
import json
import pandas as pd


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Return a deterministic SHA-256 fingerprint of dataframe values and schema.

    Includes column labels, dtypes, shape, index and values. A string-serialization
    fallback supports object columns that pandas cannot hash natively.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Dataset fingerprinting expects a pandas DataFrame.")
    digest = hashlib.sha256()
    schema = {"columns": [str(c) for c in df.columns],
              "dtypes": [str(dtype) for dtype in df.dtypes],
              "shape": list(df.shape)}
    digest.update(json.dumps(schema, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    try:
        digest.update(pd.util.hash_pandas_object(df, index=True, categorize=True).values.tobytes())
    except Exception:
        digest.update(df.astype("string").fillna("<NA>").to_csv(index=True).encode("utf-8", errors="replace"))
    return digest.hexdigest()
