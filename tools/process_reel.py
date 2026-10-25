"""Turn a downloaded reel into something Claude can read: a transcript plus a few keyframes.

Usage: process_reel.py VIDEO [--frames N] [--model NAME]

Prints a plain-text report to stdout. Results are cached next to the video
(VIDEO.transcript.txt, VIDEO.frame-N.jpg) so re-runs are instant.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Biases Whisper toward spelling automation jargon correctly ("n8n", not "and 8n")
VOCABULARY = (
    "Automation tools: n8n, Zapier, Make.com, Claude, Claude Code, ChatGPT, GPT, Gemini, "
    "Cursor, Lovable, Replit, MCP, API, webhook, Notion, Airtable, Google Sheets, Gmail, "
    "Slack, Supabase, Vercel, Perplexity, ElevenLabs, Manus, prompt, agent, workflow."
)


def probe_duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def extract_frames(video: Path, duration: float, count: int) -> list[Path]:
    frames = []
    for i in range(count):
        # Spread frames across the reel, skipping the very first/last moments
        t = duration * (i + 0.5) / count
        frame = video.with_name(f"{video.name}.frame-{i + 1}.jpg")
        if not frame.exists():
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                 "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", str(frame)],
                check=True,
            )
        frames.append(frame)
    return frames


def transcribe(video: Path, model_name: str) -> str:
    cache = video.with_name(f"{video.name}.transcript.txt")
    if cache.exists():
        return cache.read_text()

    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(video), vad_filter=True, beam_size=1, initial_prompt=VOCABULARY
    )
    lines = [f"[language: {info.language} ({info.language_probability:.0%})]"]
    for seg in segments:
        lines.append(f"[{seg.start:5.1f}s] {seg.text.strip()}")
    if len(lines) == 1:
        lines.append("(no speech detected - likely music only; rely on caption and frames)")
    text = "\n".join(lines)
    cache.write_text(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--frames", type=int, default=4)
    parser.add_argument("--model", default="small")
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.exists():
        print(f"ERROR: file not found: {video}", file=sys.stderr)
        return 1

    if video.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        # A shared photo post: nothing to transcribe, the image itself is the content
        print(f"IMAGE POST: {video}\nRead this image directly.")
        return 0

    duration = probe_duration(video)
    frames = extract_frames(video, duration, args.frames)
    transcript = transcribe(video, args.model)

    print(f"VIDEO: {video}")
    print(f"DURATION: {duration:.0f}s")
    print("\nTRANSCRIPT:")
    print(transcript)
    print("\nKEYFRAMES (read these for on-screen text, tool names, UI screenshots):")
    for frame in frames:
        print(f"- {frame}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
