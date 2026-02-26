import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import gdown
import requests
from faster_whisper import WhisperModel
from rich.console import Console


console = Console()


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def slugify_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "-", name)
    name = re.sub(r"\s+", " ", name)
    return name


def ensure_dirs(root: Path) -> tuple[Path, Path, Path]:
    videos_dir = root / "videos"
    transcripts_dir = root / "transcripts"
    tmp_dir = root / ".tmp"

    videos_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    return videos_dir, transcripts_dir, tmp_dir


def which_ffmpeg() -> Optional[str]:
    return shutil.which("ffmpeg")


def is_google_drive_url(url: str) -> bool:
    return "drive.google.com" in url or "docs.google.com" in url


def google_drive_file_id(url: str) -> Optional[str]:
    # Common patterns:
    # - https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
    # - https://drive.google.com/open?id=<FILE_ID>
    # - https://drive.google.com/uc?id=<FILE_ID>&export=download
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return None


def download_google_drive_to_videos(url: str, videos_dir: Path) -> Path:
    file_id = google_drive_file_id(url)
    if not file_id:
        raise ValueError("Could not extract Google Drive file id from URL")

    # Let gdown infer the filename; put it in videos/.
    console.print("Downloading from Google Drive...")
    output = gdown.download(id=file_id, output=str(videos_dir), quiet=False)
    if not output:
        raise RuntimeError("Google Drive download failed (file may not be public or requires a confirm page)")

    return Path(output)


def download_to_videos(url: str, videos_dir: Path) -> Path:
    if is_google_drive_url(url):
        return download_google_drive_to_videos(url, videos_dir)

    filename = url.split("?")[0].rstrip("/").split("/")[-1] or "video"
    filename = slugify_filename(filename)

    if "." not in filename:
        filename += ".mp4"

    dest = videos_dir / filename

    console.print(f"Downloading -> [bold]{dest}[/bold]")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    return dest


def resolve_input_video(input_value: str, root: Path, videos_dir: Path) -> Path:
    if is_url(input_value):
        return download_to_videos(input_value, videos_dir)

    p = Path(input_value)
    if not p.is_absolute():
        p = (root / p).resolve()

    if not p.exists():
        raise FileNotFoundError(f"Video not found: {p}")

    if p.parent != videos_dir:
        # copy into videos/ to match requested behavior
        dest = videos_dir / slugify_filename(p.name)
        if dest != p:
            console.print(f"Copying into videos/ -> [bold]{dest}[/bold]")
            shutil.copy2(p, dest)
        return dest

    return p


def extract_audio_ffmpeg(video_path: Path, out_audio: Path) -> None:
    ffmpeg = which_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it (macOS: `brew install ffmpeg`) and try again."
        )

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(out_audio),
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{proc.stderr}")


def transcribe_audio(
    audio_path: Path,
    model_size: str,
    device: str,
    compute_type: str,
    language: Optional[str],
) -> str:
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=5,
    )

    lines = []
    if info and getattr(info, "language", None):
        lines.append(f"Language: {info.language}")
        lines.append("")

    for seg in segments:
        lines.append(seg.text.strip())

    return "\n".join(lines).strip() + "\n"


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent
    videos_dir, transcripts_dir, tmp_dir = ensure_dirs(root)

    parser = argparse.ArgumentParser(description="Transcribe a video in videos/ to transcripts/.")
    parser.add_argument("input", help="URL, relative path, or absolute path to a video")
    parser.add_argument("--model", default="small", help="Whisper model size (tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="int8", help="int8/float16/float32")
    parser.add_argument("--language", default=None, help="Force language code (e.g. en). Default: auto-detect")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing transcript")

    args = parser.parse_args(argv)

    try:
        video_path = resolve_input_video(args.input, root, videos_dir)
        out_txt = transcripts_dir / f"{video_path.stem}.txt"
        if out_txt.exists() and not args.overwrite:
            console.print(f"Transcript exists: [bold]{out_txt}[/bold] (use --overwrite)")
            return 0

        tmp_audio = tmp_dir / f"{video_path.stem}.wav"

        console.print(f"Extracting audio -> [bold]{tmp_audio}[/bold]")
        extract_audio_ffmpeg(video_path, tmp_audio)

        console.print("Transcribing...")
        text = transcribe_audio(
            tmp_audio,
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
        )

        out_txt.write_text(text, encoding="utf-8")
        console.print(f"Wrote transcript -> [bold]{out_txt}[/bold]")

        return 0
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
