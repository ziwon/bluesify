"""Simple voicings: root only, and 3-7 shells."""

from __future__ import annotations

from music21 import harmony, interval, pitch

from bluesify.voicings.base import VoicingStrategy


class RootOnly(VoicingStrategy):
    """Just the root, in a target octave. Used for Level 1 left hand."""

    name = "root_only"

    def __init__(self, target_octave: int = 2) -> None:
        self.target_octave = target_octave

    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        root = chord_symbol.root()
        if root is None:
            return []
        p = pitch.Pitch(root.name)
        p.octave = self.target_octave
        return [p]


class Shell37(VoicingStrategy):
    """3rd and 7th of the chord. Classic shell voicing.

    For minor7 / dom7 / maj7 chords, gives the chord quality with two notes.
    Target register is around C3-C4 for solo piano left hand.
    """

    name = "shell_3_7"

    def __init__(self, target_octave: int = 3) -> None:
        self.target_octave = target_octave

    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        root = chord_symbol.root()
        third = chord_symbol.third
        seventh = chord_symbol.seventh

        if root is None:
            return []

        # If there is no seventh (plain triad), use the root and third
        # for L2; this still beats root-only for color.
        result: list[pitch.Pitch] = []

        if third is not None:
            third_interval = interval.Interval(root, third)
            third_pitch = pitch.Pitch(third.name)
            third_pitch.octave = self.target_octave
            # If third is below root pitch-class-wise (e.g. m3 from B is D),
            # we want it above the implied octave anchor.
            if third_interval.semitones < 0:
                third_pitch.octave = self.target_octave + 1
            result.append(third_pitch)

        if seventh is not None:
            seventh_pitch = pitch.Pitch(seventh.name)
            seventh_pitch.octave = self.target_octave
            # Seventh should sit above the third
            if result and seventh_pitch.midi <= result[-1].midi:
                seventh_pitch.octave += 1
            result.append(seventh_pitch)
        elif result:
            root_pitch = pitch.Pitch(root.name)
            root_pitch.octave = self.target_octave
            if root_pitch.midi >= result[0].midi:
                root_pitch.octave -= 1
            result.insert(0, root_pitch)
        elif not result:
            # Pure power: fall back to root
            root_pitch = pitch.Pitch(root.name)
            root_pitch.octave = self.target_octave
            result.append(root_pitch)

        return result
