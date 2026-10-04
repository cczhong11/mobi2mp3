"""Standalone Gemini Batch TTS for user-supplied plain text.

This is intentionally separate from the book conversion pipeline.  It submits
plain-text chunks to Gemini's Batch API, and a later identical invocation polls
the job, downloads WAV chunks, and merges them into one MP3.
"""

import base64
import json
import subprocess
from pathlib import Path
from typing import Any

import click
import requests

from tools import resolve_executable

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash-lite-tts"


def load_api_key(config_path: Path) -> str:
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
        key = value.get("google", {}).get("key")
    except (OSError, json.JSONDecodeError, AttributeError):
        key = None
    if not isinstance(key, str) or not key:
        raise click.ClickException("config must contain google.key")
    return key


def split_text(text: str, max_chars: int) -> list[str]:
    """Keep paragraphs intact when practical, then split oversized paragraphs."""
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
        while len(current) > max_chars:
            split_at = current.rfind("。", 0, max_chars)
            if split_at <= 0:
                split_at = max_chars
            else:
                split_at += 1
            chunks.append(current[:split_at].strip())
            current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks


def state_path_for(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".gemini-batch.json")


def batch_request(text: str, key: str, voice: str, style: str) -> dict[str, Any]:
    return {
        "key": key,
        "request": {
            "contents": [{"parts": [{"text": f"{style}\n\n{text}"}]}],
            "generation_config": {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {"voice_name": voice}
                    }
                },
            },
        },
    }


def submit(chunks: list[str], api_key: str, voice: str, style: str) -> str:
    requests_payload = []
    for index, chunk in enumerate(chunks):
        item = batch_request(chunk, f"chunk-{index:03d}", voice, style)
        item["key"] = item.pop("key")
        requests_payload.append(item)
    response = requests.post(
        f"{API_BASE}/models/{MODEL}:batchGenerateContent",
        params={"key": api_key},
        json={
            "batch": {
                "display_name": "mobi2mp3-standalone-text-tts",
                "input_config": {"requests": {"requests": requests_payload}},
            }
        },
        timeout=60,
    )
    if not response.ok:
        raise click.ClickException(f"Gemini Batch submission failed: HTTP {response.status_code}")
    name = response.json().get("name")
    if not name:
        raise click.ClickException("Gemini Batch returned no job name")
    return name


def find_audio_by_key(value: Any, results: dict[str, bytes], active_key: str | None = None) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("key"), str):
            active_key = value["key"]
        metadata = value.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("key"), str):
            active_key = metadata["key"]
        inline = value.get("inlineData") or value.get("inline_data")
        if active_key and isinstance(inline, dict) and isinstance(inline.get("data"), str):
            results[active_key] = base64.b64decode(inline["data"])
        for child in value.values():
            find_audio_by_key(child, results, active_key)
    elif isinstance(value, list):
        for child in value:
            find_audio_by_key(child, results, active_key)


def collect(job_name: str, api_key: str, state: dict[str, Any]) -> bool:
    response = requests.get(f"{API_BASE}/{job_name}", params={"key": api_key}, timeout=60)
    if not response.ok:
        raise click.ClickException(f"Gemini Batch poll failed: HTTP {response.status_code}")
    payload = response.json()
    lifecycle = payload.get("metadata", {}).get("state") or payload.get("state")
    if lifecycle not in {"JOB_STATE_SUCCEEDED", "BATCH_STATE_SUCCEEDED", "SUCCEEDED"}:
        if lifecycle in {"JOB_STATE_FAILED", "BATCH_STATE_FAILED", "FAILED", "CANCELLED"}:
            raise click.ClickException(f"Gemini Batch ended with {lifecycle}")
        click.echo(f"Gemini Batch is {lifecycle or 'pending'}; rerun later.")
        return False

    audio: dict[str, bytes] = {}
    find_audio_by_key(payload, audio)
    missing = []
    for task in state["tasks"]:
        data = audio.get(task["key"])
        if not data:
            missing.append(task["key"])
            continue
        path = Path(task["wav"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if missing:
        raise click.ClickException(
            "Gemini Batch completed without audio for: " + ", ".join(missing)
        )
    return True


def merge_wavs(tasks: list[dict[str, str]], output: Path) -> None:
    manifest = output.with_suffix(".concat.txt")
    manifest.write_text(
        "".join(f"file {Path(task['wav']).as_posix()!r}\n" for task in tasks),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                resolve_executable("ffmpeg", "/opt/homebrew/bin/ffmpeg"),
                "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                "-c:a", "libmp3lame", "-q:a", "2", str(output),
            ],
            check=True,
        )
    finally:
        manifest.unlink(missing_ok=True)


@click.command()
@click.option("--input", "input_path", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True)
@click.option("--output", type=click.Path(path_type=Path, dir_okay=False), required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=Path("key.json"), show_default=True)
@click.option("--voice", default="Kore", show_default=True)
@click.option("--style", default="Speak briskly but clearly, with natural audiobook phrasing.", show_default=True)
@click.option("--max-chars", default=3000, type=click.IntRange(min=200), show_default=True)
def main(input_path: Path, output: Path, config_path: Path, voice: str, style: str, max_chars: int) -> None:
    """Submit or collect a standalone plain-text Gemini Batch TTS job."""
    output = output.expanduser().resolve()
    state_path = state_path_for(output)
    api_key = load_api_key(config_path)
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not collect(state["job_name"], api_key, state):
            return
        merge_wavs(state["tasks"], output)
        state_path.unlink(missing_ok=True)
        click.echo(f"Created {output}")
        return

    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        raise click.ClickException("input text is empty")
    chunks = split_text(text, max_chars)
    work_dir = output.parent / f".{output.stem}.gemini-wav"
    tasks = [
        {"key": f"chunk-{index:03d}", "wav": str(work_dir / f"{index:03d}.wav")}
        for index in range(len(chunks))
    ]
    job_name = submit(chunks, api_key, voice, style)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"job_name": job_name, "tasks": tasks}, indent=2), encoding="utf-8")
    click.echo(f"Submitted {len(chunks)} chunk(s). Rerun the identical command to collect audio.")


if __name__ == "__main__":
    main()
