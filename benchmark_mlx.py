import json
import statistics
import time
from pathlib import Path

import click

from tts.config import MlxQwenTTSConfig
from tts.mlx_qwen3 import MlxQwen3TTS


def probe_duration_seconds(path: Path) -> float:
    import subprocess

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


@click.command()
@click.option("--text", "inline_text", default=None, help="Inline text to synthesize.")
@click.option(
    "--text-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to a text file to benchmark.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("/tmp/mobi2mp3-benchmark-mlx"),
    show_default=True,
)
@click.option(
    "--model",
    default="mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16",
    show_default=True,
)
@click.option("--voice", default="serena", show_default=True)
@click.option("--language", default="Chinese", show_default=True)
@click.option("--speed", default=1.0, type=float, show_default=True)
@click.option("--max-tokens", default=16000, type=int, show_default=True)
@click.option("--ref-audio", type=click.Path(path_type=Path, exists=True), default=None)
@click.option("--ref-text", default=None)
@click.option("--iterations", default=3, type=int, show_default=True)
@click.option("--warmup", default=1, type=int, show_default=True)
@click.option("--keep-audio/--no-keep-audio", default=False, show_default=True)
def main(
    inline_text: str | None,
    text_file: Path | None,
    output_dir: Path,
    model: str,
    voice: str,
    language: str,
    speed: float,
    max_tokens: int,
    ref_audio: Path | None,
    ref_text: str | None,
    iterations: int,
    warmup: int,
    keep_audio: bool,
) -> None:
    if not inline_text and not text_file:
        raise click.ClickException("Provide either --text or --text-file")
    if inline_text and text_file:
        raise click.ClickException("Use only one of --text or --text-file")
    if iterations <= 0:
        raise click.ClickException("--iterations must be > 0")
    if warmup < 0:
        raise click.ClickException("--warmup must be >= 0")

    text = inline_text or text_file.read_text()
    output_dir.mkdir(parents=True, exist_ok=True)

    tts = MlxQwen3TTS(
        MlxQwenTTSConfig(
            model=model,
            voice=voice,
            language=language,
            speed=speed,
            max_tokens=max_tokens,
            ref_audio=str(ref_audio) if ref_audio else None,
            ref_text=ref_text,
        )
    )

    total_runs = warmup + iterations
    measured_runs = []

    click.echo(
        json.dumps(
            {
                "model": model,
                "voice": voice,
                "language": language,
                "chars": len(text),
                "warmup": warmup,
                "iterations": iterations,
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
        )
    )

    for run_index in range(total_runs):
        run_type = "warmup" if run_index < warmup else "measured"
        audio_path = output_dir / f"benchmark-{run_index}.mp3"

        start = time.perf_counter()
        tts.synthesize(text, str(audio_path))
        elapsed = time.perf_counter() - start
        duration = probe_duration_seconds(audio_path)
        rtf = elapsed / duration if duration else None

        record = {
            "run": run_index,
            "type": run_type,
            "elapsed_seconds": round(elapsed, 3),
            "audio_seconds": round(duration, 3),
            "real_time_factor": round(rtf, 4) if rtf is not None else None,
            "audio_path": str(audio_path),
        }
        click.echo(json.dumps(record, ensure_ascii=False))

        if run_type == "measured":
            measured_runs.append(record)

        if not keep_audio:
            audio_path.unlink(missing_ok=True)

    summary = {
        "measured_runs": len(measured_runs),
        "avg_elapsed_seconds": round(
            statistics.mean(item["elapsed_seconds"] for item in measured_runs), 3
        ),
        "avg_audio_seconds": round(
            statistics.mean(item["audio_seconds"] for item in measured_runs), 3
        ),
        "avg_real_time_factor": round(
            statistics.mean(item["real_time_factor"] for item in measured_runs), 4
        ),
        "min_elapsed_seconds": round(
            min(item["elapsed_seconds"] for item in measured_runs), 3
        ),
        "max_elapsed_seconds": round(
            max(item["elapsed_seconds"] for item in measured_runs), 3
        ),
    }
    click.echo(json.dumps({"summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
