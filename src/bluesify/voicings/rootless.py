"""Rootless jazz piano voicings."""

from __future__ import annotations

from music21 import harmony, pitch

from bluesify.analysis.tensions import suggest_tension
from bluesify.voicings.base import VoicingStrategy


def _named_pitch(name: str, octave: int) -> pitch.Pitch:
    result = pitch.Pitch(name)
    result.octave = octave
    return result


def _stack_in_order(names: list[str], start_octave: int) -> list[pitch.Pitch]:
    result: list[pitch.Pitch] = []
    for name in names:
        candidate = _named_pitch(name, start_octave)
        while result and int(candidate.midi) <= int(result[-1].midi):
            candidate.octave = (candidate.octave or start_octave) + 1
        result.append(candidate)
    return result


def _ninth_name(chord_symbol: harmony.ChordSymbol) -> str | None:
    suggestion = suggest_tension(chord_symbol)
    if suggestion is None or not suggestion.available_tensions:
        return None
    return suggestion.available_tensions[0].split("(", maxsplit=1)[0]


def _thirteenth_name(chord_symbol: harmony.ChordSymbol) -> str | None:
    suggestion = suggest_tension(chord_symbol)
    if suggestion is None:
        return None
    for tension in suggestion.available_tensions:
        if "(13)" in tension or "(b13)" in tension:
            return tension.split("(", maxsplit=1)[0]
    return None


class RootlessAForm(VoicingStrategy):
    """A-form rootless voicing: 3-5-7-9."""

    name = "rootless_a_3_5_7_9"

    def __init__(self, target_octave: int = 3) -> None:
        self.target_octave = target_octave

    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        names = [
            p.name
            for p in [
                chord_symbol.third,
                chord_symbol.fifth,
                chord_symbol.seventh,
            ]
            if p is not None
        ]
        ninth = _ninth_name(chord_symbol)
        if ninth is not None:
            names.append(ninth)
        return _stack_in_order(names, self.target_octave)


class RootlessBForm(VoicingStrategy):
    """B-form rootless voicing: 7-9-3-13."""

    name = "rootless_b_7_9_3_13"

    def __init__(self, target_octave: int = 3) -> None:
        self.target_octave = target_octave

    def voice(self, chord_symbol: harmony.ChordSymbol) -> list[pitch.Pitch]:
        names: list[str] = []
        if chord_symbol.seventh is not None:
            names.append(chord_symbol.seventh.name)
        ninth = _ninth_name(chord_symbol)
        if ninth is not None:
            names.append(ninth)
        if chord_symbol.third is not None:
            names.append(chord_symbol.third.name)
        thirteenth = _thirteenth_name(chord_symbol)
        if thirteenth is not None:
            names.append(thirteenth)
        return _stack_in_order(names, self.target_octave)

