# bluesify

[![CI](https://github.com/ziwon/bluesify/actions/workflows/ci.yml/badge.svg)](https://github.com/ziwon/bluesify/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Step-by-step jazz/blues piano arrangement engine for self-learning.
Bluesify takes a MusicXML lead sheet, analyzes its harmony, and produces
progressive solo-piano arrangements with MIDI, MusicXML, and structured
teacher annotations.

<img src="docs/assets/background.png">

## Status

Phase 1 is implemented for Mode B: jazz-standard style lead sheets arranged for
solo piano. Levels 1-5 are playable for the copyright-safe canonical fixture.

Currently supported:

- Solo piano mode
- Jazz ballad arrangement path
- Levels 1-5
- Chord tension teaching for common jazz chord qualities
- FastAPI/static web UI with score preview and MIDI playback

Not yet implemented:

- Accompaniment mode
- Full reharmonization Mode A
- General song import pipeline
- Production deployment

## Goals

- **Mode A**: Pop/song scores -> jazz/blues reharmonization
- **Mode B**: Jazz standards -> step-by-step learning arrangements
- Performance modes: Solo piano / Accompaniment
- Each level produces MusicXML + MIDI + structured rationale
- Optional render output through Verovio when installed
- Rule-based teacher annotations, with an LLM teacher planned later

## Quick Start

```bash
# Setup
just sync

# Analyze harmony and teaching notes
just analyze

# Arrange all solo levels, 1 through 5
just arrange level=5
```

Generated files:

- `*.musicxml`
- `*.mid`
- `*.annotations.json`
- `*.svg` when `just sync-render` is installed and Verovio is available
- `*.pdf` only when the installed Verovio Python binding supports PDF export

## Web UI

Bluesify includes an iPad-first, no-build web app. FastAPI wraps the engine;
the frontend renders arranged scores with OpenSheetMusicDisplay and plays MIDI
through Tone.js.

```bash
just sync-web
just serve            # http://127.0.0.1:8000
just serve-reload     # dev auto-reload
```

Open the page, tap **Load demo** or upload your own MusicXML lead sheet, choose
a level/style, and press play.

Upload support:

- `.musicxml`
- `.xml`
- `.mxl`
- `.mid`
- `.midi`

MusicXML lead sheets with melody plus chord symbols are the recommended input.
MIDI can be parsed, but it usually lacks chord symbols, so analysis and
arrangement quality may be limited.

## Arrangement Levels

| Level | Name | Current behavior |
|-------|------|------------------|
| 1 | Root & Melody | Left-hand root under the melody |
| 2 | Shell Voicings | 3rd/7th guide-tone shells |
| 3 | Walking Bass | Quarter-note bass line between chord roots |
| 4 | Block Chords | Melody harmonized with chord tones |
| 5 | Full Arrangement | Block chords, tensions, intro/outro frames |

## Development

This is a modern `src/` layout Python project. Local workflows are exposed
through `just`; the recipes use `uv` under the hood.

```bash
just sync
just check
just serve
just arrange level=5
```

CI runs the same checks on pull requests and pushes to `main`.

## Project Layout

```text
src/bluesify/
  analysis/   Score analysis and tension suggestions
  arranger/   Arrangement engines
  core/       Score I/O, chord normalization, shared models
  render/     Optional Verovio rendering helpers
  voicings/   Piano voicing strategies
  web/        FastAPI backend + static frontend
tests/        Pytest suite with copyright-safe generated fixtures
docs/         Plans, theory notes, rule diagrams, import pipeline notes
examples/     Generated sample outputs
```

## Architecture

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#171717", "primaryColor": "#232323", "primaryTextColor": "#f5f5f5", "primaryBorderColor": "#d0d0d0", "lineColor": "#cfcfcf", "fontFamily": "Inter, Arial, sans-serif"}}}%%
flowchart TD
  A["Lead Sheet Input<br/>MusicXML / demo fixture"]
  B["Future Import Pipeline<br/>chord text<br/>full score / MIDI"]
  C["Analysis<br/>key + tempo + time<br/>chord summary"]
  D["Tension Suggestions<br/>major / minor<br/>dominant / half-dim"]
  E["Solo Arranger<br/>level + style + mode"]
  F["Voicing Strategy<br/>roots / shells<br/>block / rootless / drop-2"]
  G["Groove Pattern<br/>ballad / swing<br/>blues / shuffle"]
  H["Future Reharmonization<br/>Mode A rules"]
  I["Decision Log<br/>rationale + tags<br/>practice tips"]
  J["Render Outputs<br/>MusicXML + MIDI<br/>annotations"]
  K["Optional Verovio Render<br/>SVG / PDF when supported"]
  L["Web UI<br/>OSMD preview<br/>Tone.js playback"]

  A --> C
  B -. "planned import" .-> C
  C --> D
  D --> E
  E --> F
  E --> G
  E -. "future" .-> H
  F --> I
  G --> I
  H -. "reharm decisions" .-> I
  I --> J
  J --> K
  J --> L
  L -. "upload + preview loop" .-> A

  classDef input fill:#232323,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  classDef planned fill:#3b2f20,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px,stroke-dasharray:5 5;
  classDef analysis fill:#52676b,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  classDef arranger fill:#1b070a,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  classDef music fill:#62164d,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  classDef evidence fill:#173f32,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  classDef render fill:#5a3520,stroke:#d0d0d0,color:#f5f5f5,stroke-width:2px;
  class A input;
  class B,H planned;
  class C,D analysis;
  class E arranger;
  class F,G music;
  class I evidence;
  class J,K,L render;
```

## Import Pipeline

General songs often need conversion before Bluesify can arrange them. The
recommended future path is:

1. Chord text -> lead sheet MusicXML
2. Full MusicXML -> simplified lead sheet
3. MIDI -> inferred lead sheet with confidence warnings
4. PDF/image and audio import later

See [docs/import_pipeline.md](docs/import_pipeline.md) for the proposed design.

## License

MIT. Do not commit copyrighted source MusicXML files. Use synthesized or
verified copyright-safe fixtures for tests and demos.
