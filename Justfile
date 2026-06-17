set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

fixture := "tests/fixtures/canonical_leadsheet.musicxml"
out := "output"

# List available recipes.
default:
    just --list

# Install default development dependencies.
sync:
    uv sync

# Install web extras for the FastAPI/static UI.
sync-web:
    uv sync --extra web

# Install render extras for optional Verovio SVG/PDF output.
sync-render:
    uv sync --extra render

# Run the test suite.
test:
    uv run pytest

# Run Ruff.
lint:
    uv run ruff check .

# Run strict mypy checks.
typecheck:
    uv run mypy .

# Run all local CI checks.
check: test lint typecheck

# Analyze the canonical copyright-safe fixture.
analyze file=fixture:
    uv run bluesify analyze "{{file}}"

# Arrange the canonical fixture or a given MusicXML lead sheet.
arrange level="5" style="jazz-ballad" file=fixture:
    uv run bluesify arrange "{{file}}" --mode solo --style "{{style}}" --level "{{level}}" --out "{{out}}"

# Arrange every solo level for the canonical fixture.
arrange-all style="jazz-ballad" file=fixture:
    for level in 1 2 3 4 5; do \
      uv run bluesify arrange "{{file}}" --mode solo --style "{{style}}" --level "$level" --out "{{out}}"; \
    done

# Serve the local web UI.
serve port="8000":
    uv run bluesify serve --host 127.0.0.1 --port "{{port}}"

# Serve the local web UI with auto-reload.
serve-reload port="8000":
    uv run bluesify serve --host 127.0.0.1 --port "{{port}}" --reload

# Remove local generated output.
clean:
    rm -rf "{{out}}"
