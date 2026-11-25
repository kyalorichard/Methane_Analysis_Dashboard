"""Resolve one authoritative project/dataset/configuration context per analysis page."""
from __future__ import annotations
from typing import Any


def resolve_analysis_context(data, session_state) -> dict[str, Any]:
    """Build and cache a reproducible context shared by all analysis pages.

    This function does not mutate the dataframe. It fingerprints the active data,
    loads scoped settings, and records validation feedback for the current run.
    """
    from analysis_engine.research_intelligence import dataframe_fingerprint
    from analysis_engine.settings_config import load_active_settings, validate_settings

    if data is None:
        raise ValueError("No active dataset is available.")
    fingerprint = dataframe_fingerprint(data)
    project_id = str(session_state.get("active_project_id") or session_state.get("analysis_project_scope") or "default-project")
    dataset_id = str(session_state.get("active_dataset_id") or session_state.get("active_dataset_key") or fingerprint[:16])
    species = str(session_state.get("species") or session_state.get("active_project_species") or "other").lower()
    settings = load_active_settings(session_state)
    errors, warnings = validate_settings(settings)
    context = {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "dataset_name": str(session_state.get("data_name") or "Active dataset"),
        "dataset_fingerprint": fingerprint,
        "species": species,
        "settings": settings,
        "settings_errors": errors,
        "settings_warnings": warnings,
    }
    session_state["active_analysis_context"] = context
    session_state["active_dataset_fingerprint"] = fingerprint
    return context
