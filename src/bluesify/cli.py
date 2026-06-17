"""Bluesify CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bluesify.arranger.solo import arrange_solo
from bluesify.core.score import load_musicxml, save_midi, save_musicxml
from bluesify.core.types import Level, PerformanceMode, Style
from bluesify.render.pdf import save_pdf, save_svg

console = Console()


@click.group()
def main() -> None:
    """bluesify - step-by-step jazz/blues arrangement engine."""


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--mode", type=click.Choice(["solo", "accomp"]), default="solo")
@click.option(
    "--style",
    type=click.Choice([s.value for s in Style]),
    default=Style.JAZZ_BALLAD.value,
)
@click.option("--level", type=click.IntRange(1, 5), required=True)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("./output"))
@click.option("--title", type=str, default=None)
def arrange(
    input_path: Path,
    mode: str,
    style: str,
    level: int,
    out_dir: Path,
    title: str | None,
) -> None:
    """Arrange INPUT_PATH (MusicXML) at the given level."""
    perf_mode = PerformanceMode(mode)
    style_enum = Style(style)
    level_enum = Level(level)

    if perf_mode is not PerformanceMode.SOLO:
        raise click.ClickException("Only solo mode is implemented in Phase 1.")

    console.print(f"[cyan]Loading[/cyan] {input_path}")
    score = load_musicxml(input_path)

    console.print(f"[cyan]Arranging[/cyan] level={level} style={style}")
    out_score, result = arrange_solo(
        score,
        level=level_enum,
        style=style_enum,
        title=title or input_path.stem,
    )

    # Analysis summary
    table = Table(title="Analysis", show_header=True)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Key", result.analysis.key)
    table.add_row("Tempo", str(result.analysis.tempo_bpm or "(not set)"))
    table.add_row("Time", result.analysis.time_signature)
    table.add_row("Measures", str(result.analysis.measure_count))
    table.add_row("Top chords", ", ".join(result.analysis.chord_summary))
    if result.analysis.tension_summary:
        table.add_row(
            "Tensions",
            "; ".join(
                f"{s.chord}: {', '.join(s.available_tensions)}"
                for s in result.analysis.tension_summary
            ),
        )
    console.print(table)

    # Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{input_path.stem}_level{level}"

    xml_path = save_musicxml(out_score, out_dir / f"{stem}.musicxml")
    mid_path = save_midi(out_score, out_dir / f"{stem}.mid")
    pdf_path: Path | None = None
    svg_path: Path | None = None
    try:
        pdf_path = save_pdf(out_score, out_dir / f"{stem}.pdf")
    except RuntimeError as exc:
        console.print(f"[yellow]Skipped PDF[/yellow] {exc}")
        try:
            svg_path = save_svg(out_score, out_dir / f"{stem}.svg")
        except RuntimeError as svg_exc:
            console.print(f"[yellow]Skipped SVG[/yellow] {svg_exc}")
    ann_path = out_dir / f"{stem}.annotations.json"
    ann_path.write_text(result.model_dump_json(indent=2))

    console.print(f"[green]Wrote[/green] {xml_path}")
    console.print(f"[green]Wrote[/green] {mid_path}")
    if pdf_path is not None:
        console.print(f"[green]Wrote[/green] {pdf_path}")
    if svg_path is not None:
        console.print(f"[green]Wrote[/green] {svg_path}")
    console.print(f"[green]Wrote[/green] {ann_path}")

    if result.decisions:
        console.print(f"\n[yellow]{len(result.decisions)} decisions logged[/yellow]")
        console.print(f"  e.g. m{result.decisions[0].measure}: {result.decisions[0].rationale}")


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
def analyze_cmd(input_path: Path) -> None:
    """Analyze a score without arranging it."""
    from bluesify.analysis.key import analyze as run_analysis

    score = load_musicxml(input_path)
    result = run_analysis(score, title=input_path.stem)
    console.print(json.dumps(result.model_dump(), indent=2))


# Click can't easily rename via decorator while keeping the function name;
# re-register under "analyze".
analyze_cmd.name = "analyze"
main.add_command(analyze_cmd)


@main.command()
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev)")
def serve(host: str, port: int, reload: bool) -> None:
    """Launch the bluesify web UI (FastAPI + iPad-first frontend)."""
    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException(
            "Web extras not installed. Run: uv sync --extra web"
        ) from exc

    console.print(f"[green]Bluesify[/green] serving at [cyan]http://{host}:{port}[/cyan]")
    uvicorn.run("bluesify.web.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
