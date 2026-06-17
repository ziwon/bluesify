"""Shared groove pattern types."""

from __future__ import annotations

from dataclasses import dataclass

from music21 import pitch


@dataclass(frozen=True)
class BassEvent:
    """One left-hand bass event in a measure."""

    pitch: pitch.Pitch
    duration_quarters: float

