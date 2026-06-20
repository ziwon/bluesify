"""Solo piano arranger.

Takes an input Score with melody + chord symbols and produces a two-staff
arrangement at a target Level.

Phase 1 scope:
    Level 1 - LH: root only, RH: melody unchanged
    Level 2 - LH: shell 3-7, RH: melody unchanged
    Level 3 - LH: simple walking bass, RH: melody unchanged
    Level 4 - LH: walking bass, RH: melody + block chords
    Level 5 - LH: walking bass, RH: block chords with tensions

The melody part is assumed to be the top-most part of the input score.
Chord symbols are read from any part of the input.
"""

from __future__ import annotations

import copy
from typing import cast

from music21 import (
    chord,
    clef,
    duration,
    harmony,
    instrument,
    interval,
    metadata,
    note,
    pitch,
    stream,
)

from bluesify.analysis.key import analyze
from bluesify.analysis.tensions import suggest_tension
from bluesify.core.types import (
    ArrangementDecision,
    ArrangementResult,
    Level,
    PerformanceMode,
    Style,
)
from bluesify.grooves.base import BassEvent
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
        case Level.L3_WALKING:
            return (
                f"Walking bass under {chord_figure}. The line starts on the root, "
                "touches a chord tone, then approaches the next root.",
                ["walking-bass", "root-motion", "approach-tone"],
                [
                    "Keep the quarter notes even and connected.",
                    "Listen for how beat 4 pulls into the next bar.",
                ],
            )
        case Level.L4_BLOCK:
            return (
                f"Walking bass plus right-hand block chords for {chord_figure}. "
                "The melody stays on top while chord tones fill underneath.",
                ["walking-bass", "block-chords", "melody-on-top"],
                [
                    "Play the melody note slightly louder than the harmony below it.",
                    "Keep the left hand steady before adding right-hand weight.",
                ],
            )
        case Level.L5_FULL:
            return (
                f"Full texture for {chord_figure}: walking bass, melody block chords, "
                "and available tensions where they fit the chord quality.",
                ["walking-bass", "block-chords", "tensions"],
                [
                    "Treat tensions as color, not extra volume.",
                    "Practice the bass alone, then add the right-hand voicing.",
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


def _root_pitch(chord_symbol: harmony.ChordSymbol, octave: int) -> pitch.Pitch | None:
    root = chord_symbol.root()
    if root is None:
        return None
    result = pitch.Pitch(root.name)
    result.octave = octave
    return result


def _transpose_from_root(
    chord_symbol: harmony.ChordSymbol,
    interval_name: str,
    octave: int,
) -> pitch.Pitch | None:
    root = chord_symbol.root()
    if root is None:
        return None
    root_pitch = pitch.Pitch(root.name)
    root_pitch.octave = octave
    return cast(pitch.Pitch, interval.Interval(interval_name).transposePitch(root_pitch))


def _midi(p: pitch.Pitch) -> int:
    return int(p.midi)


def _shift_octave(p: pitch.Pitch, delta: int) -> None:
    p.octave = (p.octave or 4) + delta


def _named_pitch_below(name: str, ceiling: pitch.Pitch, max_distance: int = 18) -> pitch.Pitch | None:
    candidate = pitch.Pitch(name)
    candidate.octave = ceiling.octave
    while _midi(candidate) >= _midi(ceiling):
        _shift_octave(candidate, -1)
    if _midi(ceiling) - _midi(candidate) > max_distance:
        _shift_octave(candidate, 1)
    if _midi(candidate) >= _midi(ceiling) or _midi(ceiling) - _midi(candidate) > max_distance:
        return None
    return candidate


def _chord_tone_names(chord_symbol: harmony.ChordSymbol, include_tensions: bool) -> list[str]:
    names: list[str] = []
    for candidate in [
        chord_symbol.third,
        chord_symbol.seventh,
        chord_symbol.fifth,
        chord_symbol.root(),
    ]:
        if candidate is not None and candidate.name not in names:
            names.append(candidate.name)

    if include_tensions:
        suggestion = suggest_tension(chord_symbol)
        if suggestion is not None:
            for tension in suggestion.available_tensions[:2]:
                tension_name = tension.split("(", maxsplit=1)[0]
                if tension_name not in names:
                    names.append(tension_name)

    return names


def _block_chord_for_melody(
    melody_note: note.Note,
    chord_symbol: harmony.ChordSymbol | None,
    include_tensions: bool,
) -> chord.Chord | note.Note:
    if chord_symbol is None:
        return copy.deepcopy(melody_note)

    melody_pitch = copy.deepcopy(melody_note.pitch)
    harmony_pitches: list[pitch.Pitch] = []
    for tone_name in _chord_tone_names(chord_symbol, include_tensions):
        candidate = _named_pitch_below(tone_name, melody_pitch)
        if (
            candidate is not None
            and candidate.nameWithOctave != melody_pitch.nameWithOctave
            and all(_midi(candidate) != _midi(existing) for existing in harmony_pitches)
        ):
            harmony_pitches.append(candidate)
        if len(harmony_pitches) >= 3:
            break

    if not harmony_pitches:
        return copy.deepcopy(melody_note)

    voiced = [*sorted(harmony_pitches, key=_midi), melody_pitch]
    result = chord.Chord(voiced)
    result.duration = copy.deepcopy(melody_note.duration)
    return result


def _approach_to_next_root(
    current_root: pitch.Pitch,
    next_chord: harmony.ChordSymbol | None,
) -> pitch.Pitch:
    if next_chord is None:
        return copy.deepcopy(current_root)

    next_root = _root_pitch(next_chord, current_root.octave or 2)
    if next_root is None:
        return copy.deepcopy(current_root)
    while _midi(next_root) - _midi(current_root) > 6:
        _shift_octave(next_root, -1)
    while _midi(current_root) - _midi(next_root) > 6:
        _shift_octave(next_root, 1)

    approach = pitch.Pitch()
    approach.midi = _midi(next_root) - 1 if _midi(next_root) >= _midi(current_root) else _midi(next_root) + 1
    return approach


def _walking_bass_pitches(
    chord_symbol: harmony.ChordSymbol,
    next_chord: harmony.ChordSymbol | None,
    beats: int,
) -> list[pitch.Pitch]:
    root = _root_pitch(chord_symbol, octave=2)
    if root is None:
        return []

    chord_tones = [
        _root_pitch(chord_symbol, octave=2),
        chord_symbol.fifth,
        chord_symbol.third,
    ]
    result: list[pitch.Pitch] = []
    for candidate in chord_tones:
        if candidate is None:
            continue
        p = pitch.Pitch(candidate.name)
        p.octave = 2
        result.append(p)
        if len(result) >= max(beats - 1, 1):
            break

    while len(result) < max(beats - 1, 1):
        result.append(copy.deepcopy(root))
    if beats > 1:
        result.append(_approach_to_next_root(root, next_chord))
    return result[:beats]


def _bass_events_for_style(
    style: Style,
    chord_symbol: harmony.ChordSymbol,
    next_chord: harmony.ChordSymbol | None,
    measure_duration: float,
) -> list[BassEvent]:
    beats = max(1, int(measure_duration))
    root = _root_pitch(chord_symbol, octave=2)
    if root is None:
        return []

    match style:
        case Style.SLOW_BLUES:
            fifth = _transpose_from_root(chord_symbol, "P5", 2) or copy.deepcopy(root)
            return [
                BassEvent(copy.deepcopy(root), measure_duration / 2),
                BassEvent(fifth, measure_duration / 2),
            ]
        case Style.SHUFFLE_BLUES:
            fifth = _transpose_from_root(chord_symbol, "P5", 2) or copy.deepcopy(root)
            sixth = _transpose_from_root(chord_symbol, "M6", 2) or copy.deepcopy(root)
            pattern = [root, fifth, sixth, fifth]
            events: list[BassEvent] = []
            for idx in range(beats * 2):
                events.append(BassEvent(copy.deepcopy(pattern[idx % len(pattern)]), 0.5))
            return events
        case Style.JAZZ_BLUES:
            flat_seventh = _transpose_from_root(chord_symbol, "m7", 2) or copy.deepcopy(root)
            walking = _walking_bass_pitches(chord_symbol, next_chord, beats)
            if len(walking) >= 3:
                walking[2] = flat_seventh
            return [BassEvent(p, 1.0) for p in walking]
        case Style.JAZZ_SWING:
            walking = _walking_bass_pitches(chord_symbol, next_chord, beats)
            return [BassEvent(p, 1.0) for p in walking]
        case Style.JAZZ_BALLAD:
            walking = _walking_bass_pitches(chord_symbol, next_chord, beats)
            return [BassEvent(p, 1.0) for p in walking]


def _bar_duration_quarters(measure: stream.Measure) -> float:
    """Return the notated bar length, even if imported content overfills the measure."""
    try:
        bar_duration = float(measure.barDuration.quarterLength)
    except Exception:
        bar_duration = 0.0
    if bar_duration > 0:
        return bar_duration
    return float(measure.duration.quarterLength)


def _copy_within_bar(elem: note.GeneralNote, bar_duration: float) -> note.GeneralNote | None:
    """Copy a note/rest clipped to the active bar duration."""
    offset = float(elem.offset)
    if offset >= bar_duration:
        return None
    copied = copy.deepcopy(elem)
    copied.duration = duration.Duration(min(float(elem.quarterLength), bar_duration - offset))
    if copied.quarterLength <= 0:
        return None
    return copied


def _style_rule_name(style: Style, level: Level) -> str:
    if level not in {Level.L3_WALKING, Level.L4_BLOCK, Level.L5_FULL}:
        return "walking_bass"
    return f"{style.value.replace('-', '_')}_bass"


def _style_tags(style: Style) -> list[str]:
    match style:
        case Style.JAZZ_BALLAD:
            return ["jazz-ballad"]
        case Style.JAZZ_SWING:
            return ["jazz-swing", "walking-four"]
        case Style.SLOW_BLUES:
            return ["slow-blues", "root-fifth"]
        case Style.SHUFFLE_BLUES:
            return ["shuffle-blues", "eighth-note-shuffle"]
        case Style.JAZZ_BLUES:
            return ["jazz-blues", "blues-seventh"]


def _append_opening_context(dst: stream.Measure, src: stream.Measure, clef_obj: clef.Clef) -> None:
    dst.insert(0, clef_obj)
    for ts in src.getElementsByClass("TimeSignature"):
        dst.insert(0, copy.deepcopy(ts))
        break
    for ks in src.getElementsByClass("KeySignature"):
        dst.insert(0, copy.deepcopy(ks))
        break


def _append_arrangement_frame_measure(
    *,
    rh: stream.Part,
    lh: stream.Part,
    src_measure: stream.Measure,
    measure_number: int,
    chord_symbol: harmony.ChordSymbol,
    label: str,
    include_context: bool,
    decisions: list[ArrangementDecision],
    level: Level,
) -> None:
    measure_duration = _bar_duration_quarters(src_measure)

    rh_measure = stream.Measure(number=measure_number)
    lh_measure = stream.Measure(number=measure_number)
    if include_context:
        _append_opening_context(rh_measure, src_measure, clef.TrebleClef())
        _append_opening_context(lh_measure, src_measure, clef.BassClef())

    rh_chord_symbol = copy.deepcopy(chord_symbol)
    rh_chord_symbol.offset = 0.0
    rh_measure.insert(0.0, rh_chord_symbol)
    rh_rest = note.Rest()
    rh_rest.duration = duration.Duration(measure_duration)
    rh_measure.append(rh_rest)

    shell = Shell37(target_octave=3).voice(chord_symbol)
    if shell:
        lh_chord = chord.Chord(shell)
        lh_chord.duration = duration.Duration(measure_duration)
        lh_measure.append(lh_chord)
        voicing_midi = midi_numbers(shell)
    else:
        bass_root = _root_pitch(chord_symbol, octave=2)
        if bass_root is None:
            lh_rest = note.Rest()
            lh_rest.duration = duration.Duration(measure_duration)
            lh_measure.append(lh_rest)
            voicing_midi = []
        else:
            bass_note = note.Note(bass_root)
            bass_note.duration = duration.Duration(measure_duration)
            lh_measure.append(bass_note)
            voicing_midi = midi_numbers([bass_root])

    rh.append(rh_measure)
    lh.append(lh_measure)
    decisions.append(
        ArrangementDecision(
            measure=measure_number,
            beat=1.0,
            chord_before=chord_symbol.figure,
            chord_after=chord_symbol.figure,
            voicing_midi=voicing_midi,
            rule_applied=f"level5_{label}",
            rationale=f"Simple {label} frame using {chord_symbol.figure} to set up the tune.",
            theory_tags=["form", label, "shell"],
            level=level.value,
            practice_tips=["Keep this frame quieter than the tune statement."],
        )
    )


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
    voicing = _pick_voicing(level) if level in {Level.L1_ROOT_MELODY, Level.L2_SHELL} else None

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
    measure_number_offset = 0
    if level is Level.L5_FULL and src_measures and chord_symbols:
        opening_chord = chord_symbols[0]
        _append_arrangement_frame_measure(
            rh=rh,
            lh=lh,
            src_measure=src_measures[0],
            measure_number=1,
            chord_symbol=opening_chord,
            label="intro",
            include_context=True,
            decisions=decisions,
            level=level,
        )
        _append_arrangement_frame_measure(
            rh=rh,
            lh=lh,
            src_measure=src_measures[0],
            measure_number=2,
            chord_symbol=opening_chord,
            label="intro",
            include_context=False,
            decisions=decisions,
            level=level,
        )
        measure_number_offset = 2

    for m_idx, src_measure in enumerate(src_measures, start=1):
        # --- Build RH measure: copy melody notes/rests only ---
        output_measure_number = m_idx + measure_number_offset
        rh_measure = stream.Measure(number=output_measure_number)
        if m_idx == 1 and measure_number_offset == 0:
            _append_opening_context(rh_measure, src_measure, clef.TrebleClef())

        measure_start_offset = float(src_measure.getOffsetInHierarchy(score))
        active_chord = _extract_chord_at(measure_start_offset, chord_symbols, chord_offsets)
        measure_duration = _bar_duration_quarters(src_measure)
        next_chord = _extract_chord_at(measure_start_offset + measure_duration, chord_symbols, chord_offsets)

        if active_chord is not None:
            rh_chord_symbol = copy.deepcopy(active_chord)
            rh_chord_symbol.offset = 0.0
            rh_measure.insert(0.0, rh_chord_symbol)

        for elem in src_measure.notesAndRests:
            # Skip chord symbols here - they're not in notesAndRests, but be safe.
            if isinstance(elem, harmony.ChordSymbol):
                continue
            elem_offset = elem.offset
            copied_elem = _copy_within_bar(elem, measure_duration)
            if copied_elem is None:
                continue
            if (
                level in {Level.L4_BLOCK, Level.L5_FULL}
                and isinstance(copied_elem, note.Note)
                and not copied_elem.isRest
            ):
                note_offset = measure_start_offset + float(elem_offset)
                note_chord = _extract_chord_at(note_offset, chord_symbols, chord_offsets)
                rh_measure.insert(
                    elem_offset,
                    _block_chord_for_melody(
                        copied_elem,
                        note_chord,
                        include_tensions=level is Level.L5_FULL,
                    ),
                )
            else:
                rh_measure.insert(elem_offset, copied_elem)
        rh.append(rh_measure)

        # --- Build LH measure: one voicing or walking line per measure ---
        out_measure = stream.Measure(number=output_measure_number)
        if m_idx == 1 and measure_number_offset == 0:
            _append_opening_context(out_measure, src_measure, clef.BassClef())

        if active_chord is None:
            # No chord info - rest the measure
            r = note.Rest()
            r.duration = duration.Duration(measure_duration)
            out_measure.append(r)
        else:
            if level in {Level.L3_WALKING, Level.L4_BLOCK, Level.L5_FULL}:
                bass_events = _bass_events_for_style(
                    style,
                    active_chord,
                    next_chord,
                    float(measure_duration),
                )
                voiced_pitches = [event.pitch for event in bass_events]
                for event in bass_events:
                    bass_pitch = event.pitch
                    n = note.Note(bass_pitch)
                    n.duration = duration.Duration(event.duration_quarters)
                    out_measure.append(n)
                rule_name = _style_rule_name(style, level)
            elif voicing is not None:
                voiced_pitches = voicing.voice(active_chord)
                rule_name = voicing.name
            else:
                voiced_pitches = []
                rule_name = "unknown"

            if not voiced_pitches:
                r = note.Rest()
                r.duration = duration.Duration(measure_duration)
                out_measure.append(r)
            elif level in {Level.L1_ROOT_MELODY, Level.L2_SHELL}:
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
            tags = [*tags, *_style_tags(style)]
            decisions.append(
                ArrangementDecision(
                    measure=output_measure_number,
                    beat=1.0,
                    chord_before=active_chord.figure,
                    chord_after=active_chord.figure,
                    voicing_midi=midi_numbers(voiced_pitches),
                    rule_applied=rule_name,
                    rationale=rationale,
                    theory_tags=tags,
                    level=level.value,
                    practice_tips=tips,
                )
            )

        lh.append(out_measure)

    if level is Level.L5_FULL and src_measures and chord_symbols:
        outro_chord = chord_symbols[-1]
        outro_start = len(src_measures) + measure_number_offset + 1
        _append_arrangement_frame_measure(
            rh=rh,
            lh=lh,
            src_measure=src_measures[-1],
            measure_number=outro_start,
            chord_symbol=outro_chord,
            label="outro",
            include_context=False,
            decisions=decisions,
            level=level,
        )
        _append_arrangement_frame_measure(
            rh=rh,
            lh=lh,
            src_measure=src_measures[-1],
            measure_number=outro_start + 1,
            chord_symbol=outro_chord,
            label="outro",
            include_context=False,
            decisions=decisions,
            level=level,
        )

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
