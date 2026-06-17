"""Score rendering via optional Verovio dependency."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import Any, cast

from music21 import stream


def _toolkit() -> Any:
    try:
        verovio = cast(Any, importlib.import_module("verovio"))
    except ImportError as exc:
        raise RuntimeError("Score rendering requires: uv sync --extra render") from exc
    toolkit = verovio.toolkit()
    toolkit.setOptions({"pageWidth": 2100, "pageHeight": 2970, "scale": 45})
    return toolkit


def save_svg(score: stream.Score, path: Path | str) -> Path:
    """Render the first score page to SVG using verovio."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".musicxml") as tmp:
        score.write("musicxml", fp=tmp.name)
        toolkit = _toolkit()
        if not toolkit.loadFile(tmp.name):
            raise RuntimeError("Verovio could not load generated MusicXML")
        toolkit.renderToSVGFile(str(output_path), 1)

    return output_path


def save_pdf(score: stream.Score, path: Path | str) -> Path:
    """Render a score to PDF when the installed verovio binding supports it."""
    toolkit = _toolkit()
    render_pdf = getattr(toolkit, "renderToPDFFile", None)
    if render_pdf is None:
        raise RuntimeError("Installed verovio binding supports SVG export but not PDF export")

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".musicxml") as tmp:
        score.write("musicxml", fp=tmp.name)
        if not toolkit.loadFile(tmp.name):
            raise RuntimeError("Verovio could not load generated MusicXML")
        render_pdf(str(output_path))

    return output_path
