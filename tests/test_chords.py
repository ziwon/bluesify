"""Chord symbol normalization tests."""

from __future__ import annotations

from bluesify.core.chords import chord_symbol, normalize_chord_symbol_figure


def test_normalize_common_jazz_chord_spellings() -> None:
    assert normalize_chord_symbol_figure("Bbmaj7") == "B-maj7"
    assert normalize_chord_symbol_figure("B-maj7") == "B-maj7"
    assert normalize_chord_symbol_figure("CΔ7") == "Cmaj7"
    assert normalize_chord_symbol_figure("C-7") == "Cm7"
    assert normalize_chord_symbol_figure("Cø7") == "Cm7b5"
    assert normalize_chord_symbol_figure("C°7") == "Cdim7"


def test_chord_symbol_builder_returns_music21_chord_symbol() -> None:
    symbol = chord_symbol("Bbmaj7")

    assert symbol.figure == "B-maj7"
    assert symbol.root().name == "B-"
