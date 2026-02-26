# Context: Video Transcript Service (Python + ffmpeg + faster-whisper)

## Goal

A small local transcript “service” that:

- Takes a **video URL** or a **video path** (relative or absolute)
- Ensures the video is present under `videos/` (downloads/copies if needed)
- Uses **ffmpeg** to extract audio
- Transcribes locally using **faster-whisper** (no API key)
- Writes output transcripts to `transcripts/<video_stem>.txt`

Repo root: `video_transcript/`

## Final repo layout

- `videos/`
  - Input videos live here
- `transcripts/`
  - Output transcripts are written here (created automatically by the script)
- `.tmp/`
  - Temporary extracted audio (`.wav`) files (created automatically)
- `transcribe.py`
  - Main CLI entrypoint
- `requirements.txt`
  - Python dependencies
- `README.md`
  - Basic usage
- `.gitignore`
  - Ignores `.venv/`, `.tmp/`, `transcripts/`

## How transcription works (data flow)

1. **Input** (`transcribe.py <input>`)
   - If `<input>` is a URL (`http://` or `https://`): download into `videos/`.
   - If `<input>` is a path:
     - Resolve it against the repo root if it’s relative.
     - If it isn’t already inside `videos/`, copy it into `videos/`.

2. **Audio extraction**
   - `ffmpeg` extracts mono, 16kHz PCM WAV:
     - output path: `.tmp/<video_stem>.wav`

3. **Transcription**
   - Uses `faster_whisper.WhisperModel`.
   - Defaults:
     - model: `small`
     - device: `cpu`
     - compute type: `int8`
     - `vad_filter=True`
     - `beam_size=5`

4. **Output**
   - Writes transcript to: `transcripts/<video_stem>.txt`
   - If transcript exists, it will not overwrite unless `--overwrite` is provided.

## CLI options

`transcribe.py` supports:

- `--model` (default `small`) e.g. `tiny`, `base`, `small`, `medium`, `large-v3`
- `--device` (default `cpu`) e.g. `cpu`, `cuda`
- `--compute-type` (default `int8`) e.g. `int8`, `float16`, `float32`
- `--language` to force language (e.g. `en`), otherwise auto-detect
- `--overwrite` to overwrite existing transcript

## System dependencies installed

- **ffmpeg**
  - Required for extracting audio from video.
  - macOS typical install was via Homebrew.

## Python dependencies installed

From `requirements.txt`:

- `faster-whisper==1.0.3`
- `ctranslate2==4.5.0`
- `huggingface-hub==0.20.3`
- `requests==2.31.0`
- `rich==13.7.0`
- `gdown==5.2.0` (used for public Google Drive downloads)

Notes:

- First run will download the selected Whisper model weights.
- Some runtime warnings may appear depending on system SSL/OpenSSL and numeric ops; transcript generation can still succeed.

## Confirmed working run (local)

A successful example run was:

- Input: `videos/bleed-money sub.mp4`
- Output: `transcripts/bleed-money sub.txt`

## Repro checklist (for another AI)

- Ensure `ffmpeg` is installed and available in PATH.
- Create/activate a Python virtual environment.
- Install `requirements.txt`.
- Run `transcribe.py` on a video path or URL.

## Google Drive support

Public Google Drive links are supported.

- The script extracts the file id from common Drive URL formats.
- Download is handled by `gdown` and saved into `videos/`.
