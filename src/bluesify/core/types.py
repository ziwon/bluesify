"""Core types shared across the bluesify pipeline."""

from __future__ import annotations

from enum import Enum, StrEnum

from pydantic import BaseModel, Field


class PerformanceMode(StrEnum):
    """How the piece is to be performed."""

    SOLO = "solo"  # Solo piano: bass + chords + melody all on piano
    ACCOMP = "accomp"  # Accompaniment: comping for a melodic instrument


class GenreMode(StrEnum):
    """High-level arrangement style."""

    JAZZ = "jazz"
    BLUES = "blues"
    # Future: GOSPEL, BOSSA, etc.


class Style(StrEnum):
    """Concrete groove / feel."""

    JAZZ_BALLAD = "jazz-ballad"
    JAZZ_SWING = "jazz-swing"
    SLOW_BLUES = "slow-blues"
    SHUFFLE_BLUES = "shuffle-blues"
    JAZZ_BLUES = "jazz-blues"


class Level(int, Enum):
    """Difficulty progression."""

    L1_ROOT_MELODY = 1  # LH: root only, RH: melody
    L2_SHELL = 2  # LH: 3-7 shell, RH: melody
    L3_WALKING = 3  # LH: walking bass, RH: melody
    L4_BLOCK = 4  # LH: walking, RH: melody + block chords
    L5_FULL = 5  # + tensions, fills, intro/outro


class ArrangementDecision(BaseModel):
    """A single arrangement choice with rationale.

    This is the bridge between the rule engine and the teacher persona.
    Every non-trivial decision the arranger makes should produce one of these.
    """

    measure: int = Field(description="1-indexed measure number")
    beat: float = Field(description="Beat offset within the measure, 1.0-indexed")
    chord_before: str | None = Field(default=None, description="Chord symbol as-input")
    chord_after: str = Field(description="Chord symbol after any reharmonization")
    voicing_midi: list[int] = Field(default_factory=list, description="MIDI pitches in the voicing")
    rule_applied: str = Field(description="Identifier of the rule that fired, e.g. 'shell_3_7'")
    rationale: str = Field(description="Human-readable explanation")
    theory_tags: list[str] = Field(default_factory=list)
    level: int
    practice_tips: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Output of the analysis stage."""

    title: str | None = None
    key: str = Field(description="e.g. 'E minor'")
    tempo_bpm: int | None = None
    time_signature: str = "4/4"
    measure_count: int
    chord_summary: list[str] = Field(default_factory=list, description="Top chords by frequency")


class ArrangementResult(BaseModel):
    """Container returned by an Arranger.

    The musicxml content is held separately (music21 Score object),
    this is the structured / serializable part.
    """

    level: int
    mode: PerformanceMode
    style: Style
    analysis: AnalysisResult
    decisions: list[ArrangementDecision] = Field(default_factory=list)
