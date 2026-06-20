"""Key analysis behavior."""

from __future__ import annotations

from music21 import harmony, instrument, key, meter, note, stream

from bluesify.analysis.key import analyze


def test_analysis_prefers_written_key_signature_for_leadsheet() -> None:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, instrument.Piano())

    for idx in range(1, 5):
        measure = stream.Measure(number=idx)
        if idx == 1:
            measure.insert(0, key.KeySignature(0))
            measure.insert(0, meter.TimeSignature("4/4"))
        measure.insert(0, harmony.ChordSymbol("C"))
        melody = note.Note("G#4")
        melody.quarterLength = 4
        measure.insert(0, melody)
        part.append(measure)

    score.insert(0, part)

    assert analyze(score).key == "C major"
