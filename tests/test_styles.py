"""Style-specific solo arrangement tests."""

from __future__ import annotations

from pathlib import Path

from music21 import note, stream

from bluesify.arranger.solo import arrange_solo
from bluesify.core.score import load_musicxml
from bluesify.core.types import Level, Style


def _left_hand(score: stream.Score) -> stream.Part:
    for part in score.parts:
        if part.partName == "Piano LH":
            return part
    raise AssertionError("left-hand part not found")


def _measure(part: stream.Part, number: int) -> stream.Measure:
    result = part.measure(number)
    if result is None:
        raise AssertionError(f"measure {number} not found")
    return result


def _leadsheet() -> stream.Score:
    fixture = Path(__file__).parent / "fixtures" / "canonical_leadsheet.musicxml"
    return load_musicxml(fixture)


def test_each_style_records_distinct_bass_rule() -> None:
    leadsheet = _leadsheet()

    for style in Style:
        _, result = arrange_solo(
            leadsheet,
            level=Level.L3_WALKING,
            style=style,
            title=f"Style {style.value}",
        )

        assert result.decisions[0].rule_applied == f"{style.value.replace('-', '_')}_bass"
        assert style.value in result.decisions[0].theory_tags


def test_shuffle_blues_uses_eighth_note_bass_events() -> None:
    leadsheet = _leadsheet()
    out_score, _ = arrange_solo(
        leadsheet,
        level=Level.L3_WALKING,
        style=Style.SHUFFLE_BLUES,
        title="Shuffle Test",
    )

    first_measure_notes = [
        elem
        for elem in _measure(_left_hand(out_score), 1).notesAndRests
        if isinstance(elem, note.Note)
    ]

    assert len(first_measure_notes) == 8
    assert {float(n.duration.quarterLength) for n in first_measure_notes} == {0.5}


def test_slow_blues_uses_root_fifth_half_notes() -> None:
    leadsheet = _leadsheet()
    out_score, _ = arrange_solo(
        leadsheet,
        level=Level.L3_WALKING,
        style=Style.SLOW_BLUES,
        title="Slow Blues Test",
    )

    first_measure_notes = [
        elem
        for elem in _measure(_left_hand(out_score), 1).notesAndRests
        if isinstance(elem, note.Note)
    ]

    assert len(first_measure_notes) == 2
    assert [float(n.duration.quarterLength) for n in first_measure_notes] == [2.0, 2.0]
