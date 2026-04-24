import math
import re
import subprocess
import tempfile
from pathlib import Path

import click

from tools import resolve_executable


INDEX_PATTERN = re.compile(r"^(?P<stem>.+)-(?P<index>\d+)\.mp3$")


def numeric_index(path: Path) -> int:
    match = INDEX_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Unsupported file name format: {path.name}")
    return int(match.group("index"))


def chunk_items(items: list[Path], chunk_count: int) -> list[list[Path]]:
    base_size = len(items) // chunk_count
    remainder = len(items) % chunk_count
    chunks = []
    start = 0
    for i in range(chunk_count):
        size = base_size + (1 if i < remainder else 0)
        end = start + size
        chunks.append(items[start:end])
        start = end
    return [chunk for chunk in chunks if chunk]


def concat_mp3_group(ffmpeg: str, inputs: list[Path], output_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as manifest:
        manifest_path = Path(manifest.name)
        for item in inputs:
            manifest.write(f"file {item.as_posix()!r}\n")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest_path),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
    finally:
        manifest_path.unlink(missing_ok=True)


@click.command()
@click.option("--input-dir", required=True, type=click.Path(path_type=Path, exists=True))
@click.option("--book", "book_name", required=True, type=str)
@click.option("--segments", default=6, type=int, show_default=True)
@click.option("--suffix", default="merged6", type=str, show_default=True)
def main(input_dir: Path, book_name: str, segments: int, suffix: str) -> None:
    if segments <= 0:
        raise click.ClickException("--segments must be > 0")

    mp3_files = sorted(
        input_dir.glob(f"{book_name}-*.mp3"),
        key=numeric_index,
    )
    if not mp3_files:
        raise click.ClickException(f"No mp3 files found for {book_name} in {input_dir}")

    if segments > len(mp3_files):
        segments = len(mp3_files)

    ffmpeg = resolve_executable("ffmpeg", "/opt/homebrew/bin/ffmpeg")
    groups = chunk_items(mp3_files, segments)

    for i, group in enumerate(groups):
        output_path = input_dir / f"{book_name}-{suffix}-{i}.mp3"
        concat_mp3_group(ffmpeg, group, output_path)
        click.echo(f"{output_path} <= {len(group)} files")

    click.echo(
        f"Merged {len(mp3_files)} source files into {len(groups)} outputs in {input_dir}"
    )


if __name__ == "__main__":
    main()
