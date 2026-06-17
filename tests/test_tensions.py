"""Tests for teaching-oriented chord tension suggestions."""

from __future__ import annotations

from music21 import harmony, instrument, key, metadata, meter, note, stream

from bluesify.analysis.key import analyze
from bluesify.analysis.tensions import (
    suggest_dominant_tension,
    suggest_half_diminished_tension,
    suggest_major_tension,
    suggest_minor_tension,
)


def test_major_tension_rule_for_plain_major_seventh() -> None:
    suggestion = suggest_major_tension(harmony.ChordSymbol("Cmaj7"), detected_key=key.Key("C"))

    assert suggestion is not None
    assert suggestion.chord == "Cmaj7"
    assert suggestion.available_tensions == ["D(9)", "A(13)"]
    assert suggestion.color_tensions == ["F#(#11)"]
    assert suggestion.avoid_tensions == ["F(11)"]


def test_iv_major_treats_sharp_eleven_as_available() -> None:
    suggestion = suggest_major_tension(harmony.ChordSymbol("Fmaj7"), detected_key=key.Key("C"))

    assert suggestion is not None
    assert suggestion.available_tensions == ["G(9)", "B(#11)", "D(13)"]
    assert suggestion.color_tensions == []
    assert suggestion.avoid_tensions == ["B-(11)"]


def test_non_major_tonic_family_chords_are_not_suggested() -> None:
    assert suggest_major_tension(harmony.ChordSymbol("G7"), detected_key=key.Key("C")) is None
    assert suggest_major_tension(harmony.ChordSymbol("Cm7"), detected_key=key.Key("C")) is None


def test_minor_tension_rule_for_minor_seventh() -> None:
    suggestion = suggest_minor_tension(harmony.ChordSymbol("Cm7"))

    assert suggestion is not None
    assert suggestion.available_tensions == ["D(9)", "F(11)"]
    assert suggestion.color_tensions == ["A(13)"]
    assert suggestion.avoid_tensions == ["D-(b9)", "A-(b13)"]


def test_dominant_tension_rule_for_dominant_seventh() -> None:
    suggestion = suggest_dominant_tension(harmony.ChordSymbol("G7"))

    assert suggestion is not None
    assert suggestion.available_tensions == ["A(9)", "E(13)"]
    assert suggestion.color_tensions == ["A-(b9)", "A#(#9)", "C#(#11)", "E-(b13)"]
    assert suggestion.avoid_tensions == ["C(11)"]


def test_half_diminished_tension_rule() -> None:
    suggestion = suggest_half_diminished_tension(harmony.ChordSymbol("Cm7b5"))

    assert suggestion is not None
    assert suggestion.available_tensions == ["F(11)", "A-(b13)"]
    assert suggestion.color_tensions == ["D(9)"]
    assert suggestion.avoid_tensions == ["D-(b9)"]


def test_analyze_includes_unique_supported_tension_summaries() -> None:
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "Tension Test"

    part = stream.Part()
    part.partName = "Melody"
    part.insert(0, instrument.Piano())

    for idx, chord_figure in enumerate(
        ["Cmaj7", "Dm7", "G7", "Bm7b5", "Cmaj7"],
        start=1,
    ):
        measure = stream.Measure(number=idx)
        if idx == 1:
            measure.insert(0, key.KeySignature(0))
            measure.insert(0, meter.TimeSignature("4/4"))
        chord_symbol = harmony.ChordSymbol(chord_figure)
        chord_symbol.offset = 0.0
        measure.insert(0.0, chord_symbol)
        for beat in range(4):
            melody_note = note.Note("C5")
            melody_note.quarterLength = 1.0
            measure.insert(float(beat), melody_note)
        part.append(measure)

    score.insert(0, part)
    result = analyze(score)

    assert [suggestion.chord for suggestion in result.tension_summary] == [
        "Cmaj7",
        "Dm7",
        "G7",
        "Bm7b5",
    ]
