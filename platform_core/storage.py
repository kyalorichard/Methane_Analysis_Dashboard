"""Single storage facade for local SQLite/filesystem and cloud PostgreSQL/S3 backends.

Pages and shared UI should import this module rather than selecting backend modules
independently. Both implementations intentionally expose the same operation names.
"""
from __future__ import annotations
import os
from functools import lru_cache


def backend_name() -> str:
    from platform_core.database import configured
    selected = os.getenv(
        "PROJECT_STORAGE_BACKEND",
        "cloud" if (configured() and os.getenv("S3_BUCKET")) else "local",
    ).strip().lower()
    if selected not in {"local", "cloud"}:
        raise ValueError("PROJECT_STORAGE_BACKEND must be 'local' or 'cloud'.")
    if selected == "cloud":
        if not configured() or not os.getenv("S3_BUCKET"):
            raise RuntimeError("Cloud storage requires DATABASE_URL and S3_BUCKET. Set PROJECT_STORAGE_BACKEND=local for local storage.")
    return selected


@lru_cache(maxsize=2)
def _backend(name: str):
    if name == "local":
        from platform_core import local_workspace
        return local_workspace
    from platform_core import workspace
    return workspace


def get_backend():
    return _backend(backend_name())


def __getattr__(name: str):
    """Delegate supported storage operations to the selected backend."""
    allowed = {
        "list_projects", "create_project", "save_dataset", "list_datasets",
        "load_dataset", "get_project", "duplicate_project",
        "create_project_version", "list_project_versions",
        "save_dataset_configuration", "get_dataset_configuration",
    }
    if name not in allowed:
        raise AttributeError(name)
    return getattr(get_backend(), name)
