"""Voicing strategies: convert a ChordSymbol into a set of pitches."""

from __future__ import annotations

from abc import ABC, abstractmethod

from music21 import harmony, pitch


class VoicingStrategy(ABC):
    """Map a chord symbol to a list of concrete pitches."""

    name: str = "abstract"

    @abstractmethod
    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        """Return MIDI-pitched notes for this chord."""
        ...


def midi_numbers(pitches: list[pitch.Pitch]) -> list[int]:
    """Helper: extract MIDI pitch numbers."""
    return [int(p.midi) for p in pitches]
