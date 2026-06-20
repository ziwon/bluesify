"""Measure duration edge cases for generated arrangements."""

from __future__ import annotations

from music21 import harmony, instrument, key, meter, note, stream

from bluesify.arranger.solo import arrange_solo
from bluesify.core.types import Level, Style


def test_overfull_source_measure_is_clipped_to_time_signature() -> None:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Piano())

    for idx in range(1, 3):
        measure = stream.Measure(number=idx)
        if idx == 1:
            measure.insert(0, key.KeySignature(0))
            measure.insert(0, meter.TimeSignature("4/4"))
        measure.insert(0, harmony.ChordSymbol("C"))
        melody = note.Note("C5")
        melody.quarterLength = 4
        measure.insert(0, melody)
        if idx == 1:
            spill = note.Rest()
            spill.quarterLength = 2
            measure.insert(4, spill)
            assert measure.duration.quarterLength == 6
            assert measure.barDuration.quarterLength == 4
        part.append(measure)

    score.insert(0, part)
    out_score, _ = arrange_solo(
        score,
        level=Level.L5_FULL,
        style=Style.JAZZ_BALLAD,
        title="Overfull Measure",
    )

    for out_part in out_score.parts:
        for measure in out_part.getElementsByClass(stream.Measure):
            assert measure.duration.quarterLength == measure.barDuration.quarterLength == 4
