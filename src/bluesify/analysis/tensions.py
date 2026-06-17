"""Teaching rules for chord tensions."""

from __future__ import annotations

from collections.abc import Iterable

from music21 import harmony, interval, key, pitch

from bluesify.core.types import TensionSuggestion

MAJOR_CHORD_KINDS = {
    "major",
    "major-sixth",
    "major-seventh",
}

MINOR_CHORD_KINDS = {
    "minor",
    "minor-sixth",
    "minor-seventh",
}


def _pitch_name_at(root: pitch.Pitch, interval_name: str) -> str:
    transposed = interval.Interval(interval_name).transposePitch(root)
    return str(transposed.name)


def _format_tension(root: pitch.Pitch, interval_name: str, label: str) -> str:
    return f"{_pitch_name_at(root, interval_name)}({label})"


def _is_major_tonic_family(chord_symbol: harmony.ChordSymbol) -> bool:
    chord_kind = str(chord_symbol.chordKind or "")
    quality = str(chord_symbol.quality or "")
    if chord_kind.startswith("dominant"):
        return False
    return quality == "major" and chord_kind in MAJOR_CHORD_KINDS


def _is_minor_family(chord_symbol: harmony.ChordSymbol) -> bool:
    chord_kind = str(chord_symbol.chordKind or "")
    quality = str(chord_symbol.quality or "")
    return quality == "minor" and chord_kind in MINOR_CHORD_KINDS


def _is_dominant_family(chord_symbol: harmony.ChordSymbol) -> bool:
    chord_kind = str(chord_symbol.chordKind or "")
    return chord_kind.startswith("dominant")


def _is_half_diminished_family(chord_symbol: harmony.ChordSymbol) -> bool:
    chord_kind = str(chord_symbol.chordKind or "")
    quality = str(chord_symbol.quality or "")
    return quality == "diminished" and chord_kind == "minor-seventh"


def _is_iv_major_in_major_key(
    chord_symbol: harmony.ChordSymbol,
    detected_key: key.Key | None,
) -> bool:
    root = chord_symbol.root()
    if root is None or detected_key is None or detected_key.mode != "major":
        return False
    fourth = detected_key.pitchFromDegree(4)
    return bool(root.pitchClass == fourth.pitchClass)


def _build_suggestion(
    chord_symbol: harmony.ChordSymbol,
    root: pitch.Pitch,
    available: list[str],
    color: list[str],
    avoid: list[str],
    explanation: str,
) -> TensionSuggestion:
    return TensionSuggestion(
        chord=chord_symbol.figure,
        root=root.name,
        quality=str(chord_symbol.chordKind or chord_symbol.quality or "unknown"),
        available_tensions=available,
        color_tensions=color,
        avoid_tensions=avoid,
        explanation=explanation,
    )


def suggest_major_tension(
    chord_symbol: harmony.ChordSymbol,
    detected_key: key.Key | None = None,
) -> TensionSuggestion | None:
    """Return a teaching suggestion for supported major-family chord symbols."""
    root = chord_symbol.root()
    if root is None or not _is_major_tonic_family(chord_symbol):
        return None

    root_pitch = pitch.Pitch(root.name)
    available = [
        _format_tension(root_pitch, "M9", "9"),
        _format_tension(root_pitch, "M13", "13"),
    ]
    color = [_format_tension(root_pitch, "A11", "#11")]
    avoid = [_format_tension(root_pitch, "P11", "11")]

    if _is_iv_major_in_major_key(chord_symbol, detected_key):
        available.insert(1, color.pop())
        explanation = (
            "As a IV major chord in a major key, #11 is diatonic and gives a clear "
            "Lydian color. 9 and 13 are stable extensions."
        )
    else:
        explanation = (
            "Major-family chords usually take 9 and 13 cleanly. Natural 11 often "
            "clashes with the major 3rd; #11 is a brighter jazz color."
        )

    return _build_suggestion(
        chord_symbol=chord_symbol,
        root=root,
        available=available,
        color=color,
        avoid=avoid,
        explanation=explanation,
    )


def suggest_minor_tension(chord_symbol: harmony.ChordSymbol) -> TensionSuggestion | None:
    """Return a teaching suggestion for supported minor-family chord symbols."""
    root = chord_symbol.root()
    if root is None or not _is_minor_family(chord_symbol):
        return None

    root_pitch = pitch.Pitch(root.name)
    return _build_suggestion(
        chord_symbol=chord_symbol,
        root=root,
        available=[
            _format_tension(root_pitch, "M9", "9"),
            _format_tension(root_pitch, "P11", "11"),
        ],
        color=[_format_tension(root_pitch, "M13", "13")],
        avoid=[
            _format_tension(root_pitch, "m9", "b9"),
            _format_tension(root_pitch, "m13", "b13"),
        ],
        explanation=(
            "Minor-family chords usually take 9 and 11 naturally. 13 is a Dorian "
            "color and needs context; b9 and b13 can darken or destabilize the chord."
        ),
    )


def suggest_dominant_tension(chord_symbol: harmony.ChordSymbol) -> TensionSuggestion | None:
    """Return a teaching suggestion for supported dominant-family chord symbols."""
    root = chord_symbol.root()
    if root is None or not _is_dominant_family(chord_symbol):
        return None

    root_pitch = pitch.Pitch(root.name)
    return _build_suggestion(
        chord_symbol=chord_symbol,
        root=root,
        available=[
            _format_tension(root_pitch, "M9", "9"),
            _format_tension(root_pitch, "M13", "13"),
        ],
        color=[
            _format_tension(root_pitch, "m9", "b9"),
            _format_tension(root_pitch, "A9", "#9"),
            _format_tension(root_pitch, "A11", "#11"),
            _format_tension(root_pitch, "m13", "b13"),
        ],
        avoid=[_format_tension(root_pitch, "P11", "11")],
        explanation=(
            "Dominant chords support stable 9 and 13, while altered tensions add "
            "resolution pressure. Natural 11 usually clashes with the major 3rd."
        ),
    )


def suggest_half_diminished_tension(
    chord_symbol: harmony.ChordSymbol,
) -> TensionSuggestion | None:
    """Return a teaching suggestion for supported half-diminished chord symbols."""
    root = chord_symbol.root()
    if root is None or not _is_half_diminished_family(chord_symbol):
        return None

    root_pitch = pitch.Pitch(root.name)
    return _build_suggestion(
        chord_symbol=chord_symbol,
        root=root,
        available=[
            _format_tension(root_pitch, "P11", "11"),
            _format_tension(root_pitch, "m13", "b13"),
        ],
        color=[_format_tension(root_pitch, "M9", "9")],
        avoid=[_format_tension(root_pitch, "m9", "b9")],
        explanation=(
            "Half-diminished chords commonly take 11 and b13. Natural 9 is a "
            "smoother Locrian #2 color; b9 is darker and often less stable."
        ),
    )


def suggest_tension(
    chord_symbol: harmony.ChordSymbol,
    detected_key: key.Key | None = None,
) -> TensionSuggestion | None:
    """Return a teaching suggestion for supported chord symbols."""
    return (
        suggest_major_tension(chord_symbol, detected_key=detected_key)
        or suggest_minor_tension(chord_symbol)
        or suggest_dominant_tension(chord_symbol)
        or suggest_half_diminished_tension(chord_symbol)
    )


def suggest_tensions(
    chord_symbols: Iterable[harmony.ChordSymbol],
    detected_key: key.Key | None = None,
) -> list[TensionSuggestion]:
    """Return one suggestion per unique supported chord figure, preserving order."""
    suggestions: list[TensionSuggestion] = []
    seen: set[str] = set()
    for chord_symbol in chord_symbols:
        if chord_symbol.figure in seen:
            continue
        suggestion = suggest_tension(chord_symbol, detected_key=detected_key)
        if suggestion is None:
            continue
        seen.add(chord_symbol.figure)
        suggestions.append(suggestion)
    return suggestions


def suggest_major_tensions(
    chord_symbols: Iterable[harmony.ChordSymbol],
    detected_key: key.Key | None = None,
) -> list[TensionSuggestion]:
    """Return one suggestion per unique supported major chord figure, preserving order."""
    return [
        suggestion
        for suggestion in suggest_tensions(chord_symbols, detected_key=detected_key)
        if suggestion.quality in MAJOR_CHORD_KINDS
    ]
