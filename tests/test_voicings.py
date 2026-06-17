"""Voicing library tests."""

from __future__ import annotations

from music21 import harmony

from bluesify.voicings.base import midi_numbers
from bluesify.voicings.drop2 import Drop2Voicing
from bluesify.voicings.rootless import RootlessAForm, RootlessBForm


def test_rootless_a_form_uses_guide_tones_and_ninth() -> None:
    pitches = RootlessAForm().voice(harmony.ChordSymbol("Cmaj7"))

    assert [p.name for p in pitches] == ["E", "G", "B", "D"]
    assert midi_numbers(pitches) == sorted(midi_numbers(pitches))


def test_rootless_b_form_uses_seventh_ninth_third_thirteenth() -> None:
    pitches = RootlessBForm().voice(harmony.ChordSymbol("G7"))

    assert [p.name for p in pitches] == ["F", "A", "B", "E"]
    assert midi_numbers(pitches) == sorted(midi_numbers(pitches))


def test_drop2_lowers_second_from_top() -> None:
    close = RootlessAForm(target_octave=4).voice(harmony.ChordSymbol("Cmaj7"))
    dropped = Drop2Voicing(target_octave=4).voice(harmony.ChordSymbol("Cmaj7"))

    assert len(dropped) == 4
    assert midi_numbers(dropped) == sorted(midi_numbers(dropped))
    assert midi_numbers(dropped)[0] == midi_numbers(close)[-2] - 12
