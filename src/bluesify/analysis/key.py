"""Analyze a Score: key, tempo, chord summary."""

from __future__ import annotations

from collections import Counter

from music21 import harmony, stream, tempo

from bluesify.core.types import AnalysisResult


def analyze(score: stream.Score, title: str | None = None) -> AnalysisResult:
    """Extract high-level features from a parsed Score."""
    # Key detection - music21's analyzer uses Krumhansl-Schmuckler by default
    key_obj = score.analyze("key")
    key_str = f"{key_obj.tonic.name} {key_obj.mode}"

    # Tempo - first MetronomeMark we find, if any
    tempos = score.recurse().getElementsByClass(tempo.MetronomeMark)
    bpm: int | None = None
    for mm in tempos:
        if mm.number is not None:
            bpm = int(mm.number)
            break

    # Time signature - first one
    ts_iter = score.recurse().getElementsByClass("TimeSignature")
    ts_str = "4/4"
    for ts in ts_iter:
        ts_str = ts.ratioString
        break

    # Measure count - from the first part
    parts = list(score.parts)
    measure_count = len(parts[0].getElementsByClass("Measure")) if parts else 0

    # Chord summary - count unique chord symbols
    chord_symbols = score.recurse().getElementsByClass(harmony.ChordSymbol)
    counter: Counter[str] = Counter()
    for cs in chord_symbols:
        if cs.figure:
            counter[cs.figure] += 1
    top = [c for c, _ in counter.most_common(8)]

    return AnalysisResult(
        title=title,
        key=key_str,
        tempo_bpm=bpm,
        time_signature=ts_str,
        measure_count=measure_count,
        chord_summary=top,
    )
