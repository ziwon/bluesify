# bluesify

Step-by-step jazz/blues arrangement engine for self-learning piano.
Takes a lead sheet or score and produces level-by-level arrangements
that teach you how to play it in a jazz or blues style.

## Status

Phase 1 prototype. Solo piano, jazz ballad style, Autumn Leaves.

## Goals

- **Mode A**: Pop/song scores → jazz/blues reharmonization
- **Mode B**: Jazz standards → step-by-step learning arrangements
- Performance modes: Solo piano / Accompaniment
- Each level produces MusicXML + PDF + MIDI + structured rationale
- Rule-based "teacher" annotations (LLM-pluggable later)

## Quick start

```bash
# Setup
uv sync

# Analyze harmony and teaching notes
uv run bluesify analyze path/to/leadsheet.musicxml

# Arrange
uv run bluesify arrange path/to/leadsheet.musicxml \
    --mode solo \
    --style jazz-ballad \
    --level 5 \
    --out ./output/
```

## Web UI

An iPad-first, no-build web app (Phase 3). FastAPI wraps the engine; the
frontend renders the arranged score with OpenSheetMusicDisplay and plays it
back through a warm Tone.js piano voice. Teacher annotations, tension
analysis, and a level/style picker live in a single jazz-club-styled page.

```bash
uv sync --extra web
uv run bluesify serve            # http://127.0.0.1:8000
uv run bluesify serve --reload   # dev auto-reload
```

Open the page, tap **Load demo** (or drop in your own MusicXML), pick a level,
and press play. Levels 1-5 are playable in the solo jazz-ballad engine.

## Development

This is a modern `src/` layout Python project managed by `uv`.

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

## Project layout

```text
src/bluesify/
  analysis/   Score analysis
  arranger/   Arrangement engines
  core/       Score I/O and shared models
  voicings/   Piano voicing strategies
  web/        FastAPI backend + iPad-first static frontend
tests/        Pytest suite with copyright-safe generated fixtures
examples/     Generated sample outputs
```

## Architecture

```
Input (MusicXML / chord text)
    ↓
Analysis (key, form, chord function)
  └─ Chord tension suggestions
    ↓
Arranger (per Level, per Mode)
  ├─ Voicing strategy
  ├─ Groove pattern
  └─ Reharmonization rules
    ↓
Decision log (rationale + theory tags)
    ↓
Render (MusicXML / PDF / MIDI / annotations.json)
```

## License

MIT. Note: musicxml files for copyrighted songs are gitignored.
