"""Chord-symbol helpers."""

from __future__ import annotations

import re

from music21 import harmony, stream

ROOT_RE = re.compile(r"^([A-G])([#b]?)(.*)$")


def normalize_chord_symbol_figure(figure: str) -> str:
    """Normalize common jazz chord spellings into music21-compatible figures."""
    value = figure.strip()
    if not value:
        return value

    value = value.replace("△", "maj").replace("Δ", "maj")
    value = re.sub(r"^([A-G][#b]?)[øØ]7?$", r"\1m7b5", value)
    value = value.replace("°", "dim")

    # Common jazz minor shorthand: C-7 means Cm7. This is intentionally handled
    # before flat-root conversion, so Bb7 -> B-7 remains a flat-root dominant.
    minor_match = re.match(r"^([A-G])-(\d.*)$", value)
    if minor_match:
        return f"{minor_match.group(1)}m{minor_match.group(2)}"

    match = ROOT_RE.match(value)
    if not match:
        return value

    root, accidental, suffix = match.groups()
    if accidental == "b":
        accidental = "-"

    suffix = suffix.replace("Maj", "maj").replace("MAJ", "maj")
    return f"{root}{accidental}{suffix}"


def chord_symbol(figure: str) -> harmony.ChordSymbol:
    """Build a ChordSymbol after normalizing common jazz spellings."""
    return harmony.ChordSymbol(normalize_chord_symbol_figure(figure))


def normalize_score_chord_symbols(score: stream.Score) -> None:
    """Normalize chord symbol figures in an already-parsed score in place."""
    for chord in score.recurse().getElementsByClass(harmony.ChordSymbol):
        normalized = normalize_chord_symbol_figure(chord.figure)
        if normalized != chord.figure:
            chord.figure = normalized
