"""Level 2 arranger teaching notes."""

from __future__ import annotations

from music21 import harmony, instrument, key, meter, note, stream

from bluesify.arranger.solo import arrange_solo
from bluesify.core.types import Level, Style


def test_level2_plain_triad_note_matches_root_third_voicing() -> None:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Piano())
    measure = stream.Measure(number=1)
    measure.insert(0, key.KeySignature(0))
    measure.insert(0, meter.TimeSignature("4/4"))
    measure.insert(0, harmony.ChordSymbol("C"))
    melody = note.Note("E4")
    melody.quarterLength = 4
    measure.insert(0, melody)
    part.append(measure)
    score.insert(0, part)

    _, result = arrange_solo(
        score,
        level=Level.L2_SHELL,
        style=Style.JAZZ_BALLAD,
        title="Plain Triad",
    )

    decision = result.decisions[0]
    assert decision.voicing_midi == [48, 52]
    assert "Root-and-3rd shell" in decision.rationale
    assert "root-3rd" in decision.theory_tags
