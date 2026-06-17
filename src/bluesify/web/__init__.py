"""Bluesify web UI: FastAPI backend + static iPad-first frontend.

Phase 3 (PLAN.md) entry point. Wraps the arrangement engine behind a small
JSON API and serves a no-build single-page app that renders the arranged
score (OpenSheetMusicDisplay) and plays it back (Tone.js).
"""

from __future__ import annotations

from bluesify.web.app import create_app

__all__ = ["create_app"]
