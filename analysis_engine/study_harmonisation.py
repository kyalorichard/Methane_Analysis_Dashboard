"""Explicit cross-study phenotype harmonisation and random-effects meta-analysis.

No automatic unit conversion or phenotype equivalence is inferred. Users must
supply mappings, unit conversions and protocol metadata explicitly.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import norm

REQUIRED_PROTOCOL_FIELDS = ("species", "phenotype", "phenotype_definition", "unit",
                            "measurement_method", "instrument", "calibration_reference")

def harmonise_study_frame(frame: pd.DataFrame, *, study_id: str, species: str,
                          column_mapping: dict[str, str], unit: str,
                          phenotype: str, phenotype_definition: str,
                          measurement_method: str, instrument: str,
                          calibration_reference: str, conversion_factor: float = 1.0,
                          conversion_offset: float = 0.0) -> pd.DataFrame:
    """Map source columns to canonical roles; conversion must be explicit."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if not study_id.strip() or not species.strip() or not phenotype.strip() or not unit.strip():
        raise ValueError("study_id, species, phenotype and unit are required")
    if not np.isfinite(conversion_factor) or conversion_factor == 0 or not np.isfinite(conversion_offset):
        raise ValueError("Conversion factor must be finite and non-zero; offset must be finite")
    missing = {src for src in column_mapping.values() if src not in frame.columns}
    if missing:
        raise ValueError(f"Mapped source columns not found: {sorted(missing)}")
    out = pd.DataFrame(index=frame.index)
    for canonical, source in column_mapping.items():
        out[canonical] = frame[source]
    for role in ("methane_value", "body_weight_kg"):
        if role in out:
            out[role] = pd.to_numeric(out[role], errors="coerce")
    if "methane_value" in out:
        out["methane_value"] = out["methane_value"] * conversion_factor + conversion_offset
    metadata = {"study_id": study_id, "species": species.lower(), "phenotype": phenotype,
                "phenotype_definition": phenotype_definition, "unit": unit,
                "measurement_method": measurement_method, "instrument": instrument,
                "calibration_reference": calibration_reference,
                "conversion_factor": float(conversion_factor),
                "conversion_offset": float(conversion_offset)}
    for key, value in metadata.items():
        out[key] = value
    return out.reset_index(drop=True)

def audit_protocol_comparability(studies: pd.DataFrame) -> dict:
    """Assess exact metadata compatibility; this is a screen, not validation."""
    missing = [c for c in REQUIRED_PROTOCOL_FIELDS if c not in studies.columns]
    if missing:
        return {"comparable": False, "missing_fields": missing, "differences": {},
                "message": "Protocol metadata incomplete; comparability cannot be assessed."}
    differences = {}
    for col in REQUIRED_PROTOCOL_FIELDS:
        vals = sorted(studies[col].dropna().astype(str).unique().tolist())
        if len(vals) != 1 or studies[col].isna().any():
            differences[col] = {"values": vals, "has_missing": bool(studies[col].isna().any())}
    return {"comparable": not differences, "missing_fields": [], "differences": differences,
            "message": ("Protocol descriptors match exactly. This does not establish biological equivalence." if not differences
                        else "Studies differ in one or more protocol descriptors; do not pool without a justified harmonisation strategy.")}

def dersimonian_laird(effect, standard_error, *, confidence=.95) -> dict:
    """DerSimonian-Laird random-effects pooling of independent study effects."""
    yi=np.asarray(effect,dtype=float); sei=np.asarray(standard_error,dtype=float)
    if yi.ndim != 1 or sei.ndim != 1 or len(yi)!=len(sei):
        raise ValueError("effect and standard_error must be equal-length one-dimensional arrays")
    ok=np.isfinite(yi)&np.isfinite(sei)&(sei>0); yi,sei=yi[ok],sei[ok]
    k=len(yi)
    if k<2: raise ValueError("At least two studies with finite effects and positive SEs are required")
    if not .80<=confidence<=.99: raise ValueError("confidence must be between 0.80 and 0.99")
    vi=sei**2; wi=1/vi; fixed=np.sum(wi*yi)/np.sum(wi)
    q=float(np.sum(wi*(yi-fixed)**2)); df=k-1
    c=float(np.sum(wi)-np.sum(wi**2)/np.sum(wi))
    tau2=max(0.0,(q-df)/c) if c>0 else 0.0
    wr=1/(vi+tau2); pooled=float(np.sum(wr*yi)/np.sum(wr)); se=float(np.sqrt(1/np.sum(wr)))
    z=float(norm.ppf(1-(1-confidence)/2)); i2=max(0.0,(q-df)/q)*100 if q>0 else 0.0
    return {"n_studies":k,"pooled_effect":pooled,"standard_error":se,
            "ci_low":pooled-z*se,"ci_high":pooled+z*se,"tau_squared":tau2,
            "q_statistic":q,"q_df":df,"i_squared_percent":i2,
            "method":"DerSimonian-Laird random effects",
            "warning":"Study effects must estimate the same interpretable quantity. DL tau-squared can be imprecise with few studies; report study-level effects and consider REML/sensitivity analyses."}
