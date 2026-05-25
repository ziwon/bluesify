"""Solo piano arranger.

Takes an input Score with melody + chord symbols and produces a two-staff
arrangement at a target Level.

Phase 1 scope:
    Level 1 - LH: root only (half notes), RH: melody unchanged
    Level 2 - LH: shell 3-7 (whole notes), RH: melody unchanged

The melody part is assumed to be the top-most part of the input score.
Chord symbols are read from any part of the input.
"""

from __future__ import annotations

import copy

from music21 import (
    chord,
    clef,
    duration,
    harmony,
    instrument,
    metadata,
    note,
    stream,
)

from bluesify.analysis.key import analyze
from bluesify.core.types import (
    ArrangementDecision,
    ArrangementResult,
    Level,
    PerformanceMode,
    Style,
)
from bluesify.voicings.base import VoicingStrategy, midi_numbers
from bluesify.voicings.shell import RootOnly, Shell37


def _pick_voicing(level: Level) -> VoicingStrategy:
    match level:
        case Level.L1_ROOT_MELODY:
            return RootOnly(target_octave=2)
        case Level.L2_SHELL:
            return Shell37(target_octave=3)
        case _:
            raise NotImplementedError(f"Level {level} not yet implemented")


def _rationale_for(level: Level, chord_figure: str) -> tuple[str, list[str], list[str]]:
    """Return (rationale, theory_tags, practice_tips) for a level/chord choice."""
    match level:
        case Level.L1_ROOT_MELODY:
            return (
                f"Play the root of {chord_figure} in the left hand. "
                "This is the foundation - get the bass motion in your ear first.",
                ["root", "foundation"],
                ["Hold each root for the full measure.", "Listen to the bass line shape."],
            )
        case Level.L2_SHELL:
            return (
                f"Shell voicing (3rd and 7th) of {chord_figure}. "
                "The 3rd defines major/minor, the 7th defines dominant/maj7/min7. "
                "Two notes capture the entire chord quality.",
                ["shell", "3rd-7th", "guide-tones"],
                [
                    "Notice how 3rd and 7th move by half-step in ii-V-I.",
                    "Keep voicings in the C3-C4 range to avoid muddiness.",
                ],
            )
        case _:
            return (f"Level {level}", [], [])


def _extract_chord_at(
    target_offset: float,
    chord_symbols: list[harmony.ChordSymbol],
    chord_offsets: dict[int, float],
) -> harmony.ChordSymbol | None:
    """Find the chord symbol active at a given absolute score offset."""
    active: harmony.ChordSymbol | None = None
    for cs in chord_symbols:
        if chord_offsets[id(cs)] <= target_offset:
            active = cs
        else:
            break
    return active


def arrange_solo(
    score: stream.Score,
    level: Level,
    style: Style = Style.JAZZ_BALLAD,
    title: str | None = None,
) -> tuple[stream.Score, ArrangementResult]:
    """Arrange the input score for solo piano at the given level.

    Returns:
        (output_score, result)  where output_score is a 2-staff music21 Score
        and result contains analysis + decision log.
    """
    analysis = analyze(score, title=title)
    voicing = _pick_voicing(level)

    # Collect all chord symbols in time order, keyed by their absolute offset.
    # IMPORTANT: do not mutate ChordSymbol.offset - that's their offset within
    # their parent measure and changing it corrupts the source score.
    chord_symbols_raw = list(score.recurse().getElementsByClass(harmony.ChordSymbol))
    chord_offsets: dict[int, float] = {
        id(cs): float(cs.getOffsetInHierarchy(score)) for cs in chord_symbols_raw
    }
    chord_symbols: list[harmony.ChordSymbol] = sorted(
        chord_symbols_raw, key=lambda c: chord_offsets[id(c)]
    )

    # Build output score
    out = stream.Score()
    out.metadata = metadata.Metadata()
    out.metadata.title = f"{title or 'Untitled'} - Level {level.value}"
    out.metadata.composer = "arr. bluesify"

    # Right hand: rebuild from source measures, taking only note/rest content.
    # We avoid deepcopy + in-place mutation because removing ChordSymbols from
    # a deepcopied stream can corrupt offset bookkeeping in music21.
    parts_in = list(score.parts)
    if not parts_in:
        raise ValueError("Input score has no parts")

    rh = stream.Part()
    rh.partName = "Piano RH"
    rh.insert(0, instrument.Piano())

    # Left hand: generate one voicing per measure based on the chord at that measure's start
    lh = stream.Part()
    lh.partName = "Piano LH"
    lh.insert(0, instrument.Piano())

    decisions: list[ArrangementDecision] = []

    src_measures = list(parts_in[0].getElementsByClass(stream.Measure))
    for m_idx, src_measure in enumerate(src_measures, start=1):
        # --- Build RH measure: copy melody notes/rests only ---
        rh_measure = stream.Measure(number=m_idx)
        if m_idx == 1:
            rh_measure.insert(0, clef.TrebleClef())
            for ts in src_measure.getElementsByClass("TimeSignature"):
                rh_measure.insert(0, copy.deepcopy(ts))
                break
            for ks in src_measure.getElementsByClass("KeySignature"):
                rh_measure.insert(0, copy.deepcopy(ks))
                break

        for elem in src_measure.notesAndRests:
            # Skip chord symbols here - they're not in notesAndRests, but be safe.
            if isinstance(elem, harmony.ChordSymbol):
                continue
            rh_measure.insert(elem.offset, copy.deepcopy(elem))
        rh.append(rh_measure)

        # --- Build LH measure: one voicing per measure ---
        out_measure = stream.Measure(number=m_idx)
        if m_idx == 1:
            out_measure.insert(0, clef.BassClef())
            for ts in src_measure.getElementsByClass("TimeSignature"):
                out_measure.insert(0, copy.deepcopy(ts))
                break
            for ks in src_measure.getElementsByClass("KeySignature"):
                out_measure.insert(0, copy.deepcopy(ks))
                break

        measure_start_offset = float(src_measure.getOffsetInHierarchy(score))
        active_chord = _extract_chord_at(measure_start_offset, chord_symbols, chord_offsets)
        measure_duration = src_measure.duration.quarterLength

        if active_chord is None:
            # No chord info - rest the measure
            r = note.Rest()
            r.duration = duration.Duration(measure_duration)
            out_measure.append(r)
        else:
            voiced_pitches = voicing.voice(active_chord)
            if not voiced_pitches:
                r = note.Rest()
                r.duration = duration.Duration(measure_duration)
                out_measure.append(r)
            else:
                # Render as a chord (or single note) lasting the full measure
                if len(voiced_pitches) == 1:
                    n = note.Note(voiced_pitches[0])
                    n.duration = duration.Duration(measure_duration)
                    out_measure.append(n)
                else:
                    c = chord.Chord(voiced_pitches)
                    c.duration = duration.Duration(measure_duration)
                    out_measure.append(c)

                # Log the decision
                rationale, tags, tips = _rationale_for(level, active_chord.figure)
                decisions.append(
                    ArrangementDecision(
                        measure=m_idx,
                        beat=1.0,
                        chord_before=active_chord.figure,
                        chord_after=active_chord.figure,
                        voicing_midi=midi_numbers(voiced_pitches),
                        rule_applied=voicing.name,
                        rationale=rationale,
                        theory_tags=tags,
                        level=level.value,
                        practice_tips=tips,
                    )
                )

        lh.append(out_measure)

    out.insert(0, rh)
    out.insert(0, lh)

    result = ArrangementResult(
        level=level.value,
        mode=PerformanceMode.SOLO,
        style=style,
        analysis=analysis,
        decisions=decisions,
    )
    return out, result
