# Repository Guidelines

## Project Structure & Module Organization

Bluesify is a Python 3.12 prototype for generating step-by-step jazz/blues piano arrangements from MusicXML. Source code uses a `src/` layout: `src/bluesify/cli.py` defines the Click CLI, `analysis/` handles score analysis, `arranger/` contains arrangement engines, `core/` contains MusicXML/MIDI I/O and Pydantic models, and `voicings/` contains piano voicing strategies. Tests live in `tests/`; generated sample outputs live in `examples/output/`.

## Build, Test, and Development Commands

- `uv sync`: create/update the local environment, including the default `dev` dependency group.
- `uv run bluesify arrange path/to/leadsheet.musicxml --mode solo --style jazz-ballad --level 3 --out ./output`: run the arranger CLI.
- `uv run bluesify analyze path/to/leadsheet.musicxml`: print analysis JSON for a score.
- `uv run pytest`: run tests discovered as `test_*.py`.
- `uv run ruff check .`: lint imports, naming, pyupgrade rules, bugbear checks, and Ruff rules.
- `uv run mypy .`: run strict type checking.

## Coding Style & Naming Conventions

Use Python 3.12 features and typed interfaces throughout. Ruff is configured for 100-character lines, `py312`, import sorting, naming checks, and modernization rules; keep code formatted so `ruff check .` passes. Prefer clear snake_case names for functions and variables, PascalCase for classes and enums, and small pure helpers for theory/voicing logic. Preserve explicit domain names such as `Level.L2_SHELL`, `Style.JAZZ_BALLAD`, and `ArrangementDecision`.

## Testing Guidelines

Tests use `pytest`; configured discovery expects files named `test_*.py` under `tests/`. Keep fixtures copyright-safe: follow `tests/test_smoke.py`, which synthesizes a short lead sheet instead of committing protected songs. Add focused tests for analysis, voicing selection, arrangement decisions, and output serialization whenever behavior changes. Run `uv run pytest` before submitting changes; use `uv run pytest --cov` when touching shared pipeline logic.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so use concise imperative commit subjects such as `add level 3 voicing rules` or `fix musicxml output path`. Pull requests should describe the musical behavior changed, list test commands run, and include before/after output examples when generated MusicXML, MIDI, or annotations change. Link related issues and note any limitations, especially unimplemented modes such as accompaniment.

## Security & Configuration Tips

Do not commit copyrighted source MusicXML files or large generated output directories. Keep local render dependencies, API keys, and user-specific paths out of tracked files; prefer command-line options such as `--out ./output` for generated artifacts.
