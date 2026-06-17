"""FastAPI application wrapping the bluesify arrangement engine.

Endpoints
---------
GET  /                 -> the single-page app (static/index.html)
GET  /api/health       -> liveness probe
GET  /api/options      -> styles / levels metadata for the UI
GET  /api/demo         -> a copyright-safe demo lead sheet (MusicXML)
POST /api/analyze      -> AnalysisResult for an uploaded score
POST /api/arrange      -> ArrangementResult + arranged MusicXML + MIDI

The frontend never touches music21: the backend returns plain MusicXML
strings (rendered by OpenSheetMusicDisplay) and base64 MIDI (played by
Tone.js), so the UI stays a dependency-light, no-build static bundle.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from music21 import converter, stream
from music21.musicxml.m21ToXml import GeneralObjectExporter

from bluesify.analysis.key import analyze as run_analysis
from bluesify.arranger.solo import arrange_solo
from bluesify.core.chords import chord_symbol, normalize_score_chord_symbols
from bluesify.core.types import Level, Style

STATIC_DIR = Path(__file__).parent / "static"

SUPPORTED_LEVELS = {level.value for level in Level}

LEVEL_META: list[dict[str, Any]] = [
    {"value": 1, "name": "Root & Melody", "blurb": "Left-hand roots under the tune. Hear the bass move."},
    {"value": 2, "name": "Shell Voicings", "blurb": "3rd & 7th guide tones. The chord's true colour."},
    {"value": 3, "name": "Walking Bass", "blurb": "Quarter-note lines that stride between chords."},
    {"value": 4, "name": "Block Chords", "blurb": "Locked-hands melody harmonised below."},
    {"value": 5, "name": "Full Arrangement", "blurb": "Tensions, fills, intro & outro."},
]

STYLE_META: list[dict[str, str]] = [
    {"value": Style.JAZZ_BALLAD.value, "name": "Jazz Ballad"},
    {"value": Style.JAZZ_SWING.value, "name": "Jazz Swing"},
    {"value": Style.SLOW_BLUES.value, "name": "Slow Blues"},
    {"value": Style.SHUFFLE_BLUES.value, "name": "Shuffle Blues"},
    {"value": Style.JAZZ_BLUES.value, "name": "Jazz Blues"},
]


def _score_to_musicxml(score: stream.Score) -> str:
    """Serialise a music21 Score to a MusicXML string, in memory."""
    return GeneralObjectExporter(score).parse().decode("utf-8")


def _score_to_midi_b64(score: stream.Score) -> str:
    """Serialise a music21 Score to base64-encoded MIDI bytes."""
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=True) as tmp:
        score.write("midi", fp=tmp.name)
        data = Path(tmp.name).read_bytes()
    return base64.b64encode(data).decode("ascii")


def _load_upload(file: UploadFile, raw: bytes) -> stream.Score:
    """Parse an uploaded MusicXML payload into a music21 Score."""
    name = (file.filename or "score.musicxml").lower()
    fmt = "musicxml"
    if name.endswith((".mid", ".midi")):
        fmt = "midi"
    try:
        parsed = converter.parse(raw, format=fmt)
    except Exception as exc:  # music21 raises a grab-bag of exceptions
        raise HTTPException(status_code=422, detail=f"Could not parse score: {exc}") from exc
    if not isinstance(parsed, stream.Score):
        score = stream.Score()
        score.append(parsed)
        normalize_score_chord_symbols(score)
        return score
    normalize_score_chord_symbols(parsed)
    return parsed


def _build_demo_score() -> stream.Score:
    """A copyright-safe 8-bar ii-V-i lead sheet (shares the test fixture shape)."""
    from music21 import instrument, key, metadata, meter, note, tempo

    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "Demo Lead Sheet"

    part = stream.Part()
    part.partName = "Melody"
    part.insert(0, instrument.Piano())

    chords = ["Cm7b5", "F7", "B-maj7", "E-maj7", "Am7b5", "D7", "Gm7", "Gm7"]
    melodies = [
        ["C5", "E-5", "G-5", "B-5"],
        ["A4", "C5", "E-5", "F5"],
        ["B-4", "D5", "F5", "A5"],
        ["E-5", "G5", "B-5", "D6"],
        ["A4", "C5", "E-5", "G5"],
        ["F#4", "A4", "C5", "E5"],
        ["G4", "B-4", "D5", "F5"],
        ["G4", "G4", "G4", "G4"],
    ]

    for i, (ch_fig, mel) in enumerate(zip(chords, melodies, strict=True), start=1):
        m = stream.Measure(number=i)
        if i == 1:
            m.insert(0, key.KeySignature(-2))
            m.insert(0, meter.TimeSignature("4/4"))
            m.insert(0, tempo.MetronomeMark(number=72))
        cs = chord_symbol(ch_fig)
        cs.offset = 0.0
        m.insert(0.0, cs)
        for j, pitch_name in enumerate(mel):
            n = note.Note(pitch_name)
            n.quarterLength = 1.0
            m.insert(float(j), n)
        part.append(m)

    score.insert(0, part)
    return score


def create_app() -> FastAPI:
    app = FastAPI(title="Bluesify", version="0.1.0", docs_url="/api/docs")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/options")
    def options() -> dict[str, Any]:
        return {
            "levels": LEVEL_META,
            "styles": STYLE_META,
            "supported_levels": sorted(SUPPORTED_LEVELS),
        }

    @app.get("/api/demo")
    def demo() -> Response:
        xml = _score_to_musicxml(_build_demo_score())
        return Response(content=xml, media_type="application/vnd.recordare.musicxml+xml")

    @app.post("/api/analyze")
    async def analyze(file: UploadFile) -> JSONResponse:
        raw = await file.read()
        score = _load_upload(file, raw)
        title = Path(file.filename or "score").stem
        result = run_analysis(score, title=title)
        return JSONResponse(result.model_dump())

    @app.post("/api/arrange")
    async def arrange(
        file: UploadFile,
        level: int = Form(...),
        style: str = Form(Style.JAZZ_BALLAD.value),
    ) -> JSONResponse:
        if level not in SUPPORTED_LEVELS:
            raise HTTPException(
                status_code=422,
                detail=f"Level {level} is on the roadmap but not playable yet. "
                f"Try {sorted(SUPPORTED_LEVELS)}.",
            )
        try:
            style_enum = Style(style)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown style: {style}") from exc

        raw = await file.read()
        score = _load_upload(file, raw)
        title = Path(file.filename or "score").stem

        try:
            out_score, result = arrange_solo(
                score, level=Level(level), style=style_enum, title=title
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return JSONResponse(
            {
                "result": result.model_dump(),
                "musicxml": _score_to_musicxml(out_score),
                "midi_b64": _score_to_midi_b64(out_score),
            }
        )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    # Static assets (css/js/fonts). Mounted last so /api routes win.
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
