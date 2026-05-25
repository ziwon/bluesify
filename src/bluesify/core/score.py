"""Score I/O wrapping music21."""

from __future__ import annotations

from pathlib import Path

from music21 import converter, stream


def load_musicxml(path: Path | str) -> stream.Score:
    """Load a MusicXML file as a music21 Score.

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if the file is not a parseable score.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Score not found: {p}")

    parsed = converter.parse(p)
    if not isinstance(parsed, stream.Score):
        # Some single-part files parse as Part - wrap them.
        score = stream.Score()
        score.append(parsed)
        return score
    return parsed


def save_musicxml(score: stream.Score, path: Path | str) -> Path:
    """Write a Score to MusicXML. Returns the resolved path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(p))
    return p


def save_midi(score: stream.Score, path: Path | str) -> Path:
    """Write a Score to MIDI."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    score.write("midi", fp=str(p))
    return p
