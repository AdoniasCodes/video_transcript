# Video Transcript Service (local)

This repo transcribes videos you put in `videos/` and writes transcripts to `transcripts/` using **ffmpeg** + **faster-whisper**.

## Prereqs

- Python 3.10+
- `ffmpeg`

macOS:

```bash
brew install ffmpeg
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Transcribe a video already in `videos/`:

```bash
python transcribe.py "videos/bleed-money sub.mp4"
```

Or give an absolute/relative path (it will copy it into `videos/` first):

```bash
python transcribe.py "/path/to/my_video.mp4"
```

Or a URL (it will download into `videos/`):

```bash
python transcribe.py "https://example.com/video.mp4"
```

Output:

- `transcripts/<video_name>.txt`

## Notes

- Default model is `small` on CPU with `int8` compute.
- For better accuracy (slower), try `--model medium`.
- If you have CUDA, try `--device cuda --compute-type float16`.
