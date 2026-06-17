"""Smoke test: synthesize a tiny lead sheet and run the full Level 1/2 pipeline.

We avoid Autumn Leaves's copyright by using its harmonic shape (ii-V-i in
E minor) on a generic placeholder melody. This validates the engine end-to-end.
"""

from __future__ import annotations

from pathlib import Path

from music21 import harmony, instrument, key, metadata, meter, note, stream, tempo

from bluesify.arranger.solo import arrange_solo
from bluesify.core.score import load_musicxml, save_midi, save_musicxml
from bluesify.core.types import Level, Style


def build_test_leadsheet() -> stream.Score:
    """Build a minimal lead sheet: 8 measures, ii-V-i in E minor variants."""
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "Test Lead Sheet"

    part = stream.Part()
    part.partName = "Melody"
    part.insert(0, instrument.Piano())

    # Chord progression: Cm7b5 | F7 | Bbmaj7 | Ebmaj7 | Am7b5 | D7 | Gm | Gm
    # (a fragment of Autumn Leaves' bridge shape, in Bb major / G minor)
    chords = [
        "Cm7b5",
        "F7",
        "B-maj7",
        "E-maj7",
        "Am7b5",
        "D7",
        "Gm7",
        "Gm7",
    ]
    # Melody: walking quarters on chord tones (placeholder, original notes)
    # m1: C-Eb-Gb-Bb (Cm7b5 arpeggio)
    # m2: A-C-Eb-F (F7 chord tones)
    # ...just simple chord-tone melodies to verify the pipeline.
    melodies = [
        ["C5", "E-5", "G-5", "B-5"],
        ["A4", "C5", "E-5", "F5"],
        ["B-4", "D5", "F5", "A5"],
        ["E-5", "G5", "B-5", "D6"],
        ["A4", "C5", "E-5", "G5"],
        ["F#4", "A4", "C5", "E5"],
        ["G4", "B-4", "D5", "F5"],
        ["G4", "G4", "G4", "G4"],
    ]

    for i, (ch_fig, mel) in enumerate(zip(chords, melodies, strict=True), start=1):
        m = stream.Measure(number=i)
        if i == 1:
            m.insert(0, key.KeySignature(-2))  # Bb major / G minor: 2 flats
            m.insert(0, meter.TimeSignature("4/4"))
            m.insert(0, tempo.MetronomeMark(number=72))
        # Chord symbol at beat 1
        cs = harmony.ChordSymbol(ch_fig)
        cs.offset = 0.0
        m.insert(0.0, cs)
        # Melody notes
        for j, pitch_name in enumerate(mel):
            n = note.Note(pitch_name)
            n.quarterLength = 1.0
            m.insert(float(j), n)
        part.append(m)

    score.insert(0, part)
    return score


def test_all_solo_levels_pipeline(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    leadsheet = build_test_leadsheet()
    input_path = save_musicxml(leadsheet, out_dir / "input.musicxml")
    assert input_path.exists()

    for level in Level:
        out_score, result = arrange_solo(
            leadsheet,
            level=level,
            style=Style.JAZZ_BALLAD,
            title="Test Lead Sheet",
        )

        assert result.level == level.value
        assert result.analysis.measure_count == 8
        expected_decisions = 12 if level is Level.L5_FULL else 8
        assert len(result.decisions) == expected_decisions

        stem = f"test_level{level.value}"
        xml_path = save_musicxml(out_score, out_dir / f"{stem}.musicxml")
        midi_path = save_midi(out_score, out_dir / f"{stem}.mid")
        ann_path = out_dir / f"{stem}.annotations.json"
        ann_path.write_text(result.model_dump_json(indent=2))

        assert xml_path.exists()
        assert midi_path.exists()
        assert ann_path.exists()


def test_canonical_fixture_is_parseable() -> None:
    fixture = Path(__file__).parent / "fixtures" / "canonical_leadsheet.musicxml"

    score = load_musicxml(fixture)
    _, result = arrange_solo(
        score,
        level=Level.L5_FULL,
        style=Style.JAZZ_BALLAD,
        title="Canonical Lead Sheet",
    )

    assert result.analysis.measure_count == 8
    assert len(result.decisions) == 12
    assert result.decisions[-1].level == Level.L5_FULL.value
