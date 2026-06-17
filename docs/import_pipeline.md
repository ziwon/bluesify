# Import Pipeline: General Song to Lead Sheet MusicXML

Bluesify works best when the input is already a lead sheet: melody plus chord
symbols in MusicXML. General song inputs often need a conversion step before
the arranger can produce useful level-by-level piano output.

## Problem

Common input formats contain different musical information:

| Input | What it usually has | Main gap |
|-------|----------------------|----------|
| Chord text | Chord progression | No melody |
| MIDI | Notes and timing | Usually no chord symbols |
| Full MusicXML | Multiple parts | Not simplified into melody + chords |
| PDF/image | Visual notation | Needs OMR and correction |
| Audio | Sound only | Needs transcription and chord detection |

The target intermediate format should be a copyright-safe, normalized
MusicXML lead sheet with:

- one melody part
- chord symbols at useful rhythmic positions
- key, time signature, and tempo metadata where available
- normalized chord spelling accepted by `music21`

## Recommended Implementation Order

### 1. Chord Text to Lead Sheet

This is the lowest-risk first step.

Example CLI:

```bash
uv run bluesify import chords chords.txt \
  --key C \
  --time 4/4 \
  --tempo 72 \
  --out lead.musicxml
```

Example input:

```text
Cmaj7 | G7 | Am7 | Fmaj7
Dm7 G7 | Cmaj7 | Fmaj7 | G7
```

Output:

- MusicXML score with empty/rest melody measures
- chord symbols inserted at measure or beat positions
- key/time/tempo metadata

This immediately enables harmonic analysis, tension teaching, and future
reharmonization workflows even when no melody is available yet.

### 2. Full MusicXML to Lead Sheet Extractor

Use this when the user has a full score or piano arrangement.

Proposed behavior:

- choose the highest or user-selected part as melody
- preserve existing chord symbols if present
- collapse to one melody staff
- optionally infer chord symbols if missing

Example CLI:

```bash
uv run bluesify import musicxml full_score.musicxml \
  --melody-part "Voice" \
  --out lead.musicxml
```

### 3. MIDI to Simplified Lead Sheet

MIDI can be useful but is less reliable because it usually lacks harmonic
labels.

Proposed behavior:

- select top-line melody by pitch/register and note density
- estimate chord roots/qualities from vertical pitch content per measure
- emit low-confidence chord symbols with annotations

Example CLI:

```bash
uv run bluesify import midi song.mid --out lead.musicxml
```

Limitations:

- quantization affects chord inference
- accompaniment textures can confuse melody extraction
- enharmonic spelling may need key-aware cleanup

### 4. PDF/Image to MusicXML

This should come later. OMR tools such as Audiveris can produce MusicXML, but
the results usually need a correction UI.

Suggested approach:

- integrate Audiveris as an optional Docker-backed import path
- show detected melody/chords for correction before arranging
- avoid committing scanned copyrighted source material

### 5. Audio to Lead Sheet

This is the hardest path and should remain a future phase.

Required components:

- pitch/onset transcription
- beat and bar detection
- chord recognition
- melody/accompaniment separation

## Data Model Notes

A future import result should preserve confidence and provenance:

```python
class ImportResult(BaseModel):
    source_type: str
    lead_sheet_path: Path
    warnings: list[str]
    inferred_chords: bool
    confidence: float | None
```

For uncertain imports, the arranger should surface warnings before generating
an arrangement.

## Phase Recommendation

Start with `bluesify import chords` and `bluesify import musicxml`.

These cover the most practical workflows without requiring OMR or audio
transcription, and they produce clean MusicXML lead sheets that the existing
analysis, tension, and arrangement engine can already consume.
