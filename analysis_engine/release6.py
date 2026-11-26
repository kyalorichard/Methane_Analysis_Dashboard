"""Backward-compatible imports for the former release6 module.

New application code should import from :mod:`analysis_engine.research_methods`.
This shim is retained for older integrations and saved scripts only.
"""
from .research_methods import *  # noqa: F401,F403
