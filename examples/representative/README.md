# Representative Example: Geudaeman Itdamyeon Harmony Study

This folder contains Bluesify's representative song-style example.

The example is intentionally **harmony-only**:

- no lyrics
- no melody transcription
- no third-party lead-sheet scan
- chord symbols plus section/function text only

It is meant to exercise Bluesify's current strengths: harmonic analysis,
tension teaching, solo-piano jazz-ballad texture generation, and annotation
output.

## Input

- `geudaeman-itdamyeon-c-harmony.musicxml`

The source harmony was transposed from Eb major down a minor third into C for
easier piano study. The important harmonic devices are preserved:

- `F -> Fm`: IV -> borrowed iv modal interchange
- `A -> Dm`: V/ii -> ii secondary dominant motion
- `Gsus4 -> G7 -> C`: dominant suspension cadence
- `B` and `E`: chromatic passing dominant colors

## Analyze

```bash
uv run bluesify analyze examples/representative/geudaeman-itdamyeon-c-harmony.musicxml
```

Because the file is harmony-only, automatic key detection may infer a nearby key
from chord content. The chart is intended as a C-transposed study chart.

## Arrange

```bash
uv run bluesify arrange examples/representative/geudaeman-itdamyeon-c-harmony.musicxml \
  --mode solo \
  --style jazz-ballad \
  --level 5 \
  --out examples/output/representative
```

Generated MusicXML, MIDI, annotations, and render files should stay under
`examples/output/`; that directory is ignored by git.

## Preview

The current Level 5 preview is kept as a docs asset:

![Level 5 jazz-ballad preview](../../docs/assets/geudaeman-itdamyeon-c-level5-preview.svg)

## Case Study

See the full harmony and arrangement analysis:

- [Geudaeman Itdamyeon / Even If case study](../../docs/case_studies/geudaeman_itdamyeon.md)
