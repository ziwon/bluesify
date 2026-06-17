"""Drop-2 voicing helper."""

from __future__ import annotations

from music21 import harmony, pitch

from bluesify.voicings.base import VoicingStrategy
from bluesify.voicings.rootless import RootlessAForm


class Drop2Voicing(VoicingStrategy):
    """Create a compact drop-2 voicing from a close rootless stack."""

    name = "drop2"

    def __init__(self, target_octave: int = 4) -> None:
        self.target_octave = target_octave

    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        close = RootlessAForm(target_octave=self.target_octave).voice(chord_symbol)
        if len(close) < 4:
            return close

        dropped = [pitch.Pitch(p.nameWithOctave) for p in close]
        dropped[-2].octave = (dropped[-2].octave or self.target_octave) - 1
        return sorted(dropped, key=lambda p: int(p.midi))
