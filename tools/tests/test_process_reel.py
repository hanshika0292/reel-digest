import subprocess
import sys
import types

import pytest

import process_reel


class FakeRun:
    """Stands in for subprocess.run so the tests need neither ffmpeg nor ffprobe."""

    def __init__(self, duration=30.0):
        self.duration = duration
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, 0, stdout=f'{{"format": {{"duration": "{self.duration}"}}}}')
        if cmd[0] == "ffmpeg":
            open(cmd[-1], "wb").close()
            return subprocess.CompletedProcess(cmd, 0)
        raise AssertionError(f"unexpected command: {cmd}")


@pytest.fixture
def fake_run(monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(process_reel.subprocess, "run", run)
    return run


@pytest.fixture
def fake_whisper(monkeypatch):
    """Installs a fake faster_whisper module; returns the list of transcribe() calls."""
    calls = []
    segments = [types.SimpleNamespace(start=0.0, text=" Open n8n "), types.SimpleNamespace(start=4.2, text="Add a webhook")]

    class WhisperModel:
        def __init__(self, name, **kwargs):
            self.name = name

        def transcribe(self, path, **kwargs):
            calls.append((self.name, path, kwargs))
            return iter(segments), types.SimpleNamespace(language="en", language_probability=0.98)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=WhisperModel))
    return types.SimpleNamespace(calls=calls, segments=segments)


def test_probe_duration(tmp_path, fake_run):
    assert process_reel.probe_duration(tmp_path / "v.mp4") == 30.0


def test_extract_frames_spreads_timestamps_and_caches(tmp_path, fake_run):
    video = tmp_path / "v.mp4"
    frames = process_reel.extract_frames(video, 40.0, 4)
    assert [f.name for f in frames] == [f"v.mp4.frame-{i}.jpg" for i in range(1, 5)]
    assert [c[c.index("-ss") + 1] for c in fake_run.calls] == ["5.00", "15.00", "25.00", "35.00"]

    fake_run.calls.clear()
    process_reel.extract_frames(video, 40.0, 4)
    assert fake_run.calls == []


def test_transcribe_formats_segments_and_caches(tmp_path, fake_whisper):
    video = tmp_path / "v.mp4"
    text = process_reel.transcribe(video, "small")
    assert text == "[language: en (98%)]\n[  0.0s] Open n8n\n[  4.2s] Add a webhook"
    assert fake_whisper.calls[0][2]["initial_prompt"] == process_reel.VOCABULARY
    assert (tmp_path / "v.mp4.transcript.txt").read_text() == text

    process_reel.transcribe(video, "small")
    assert len(fake_whisper.calls) == 1


def test_transcribe_notes_music_only_reels(tmp_path, fake_whisper):
    fake_whisper.segments.clear()
    text = process_reel.transcribe(tmp_path / "v.mp4", "small")
    assert "no speech detected" in text


def run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["process_reel.py", *map(str, args)])
    return process_reel.main()


def test_main_missing_file(tmp_path, monkeypatch, capsys):
    assert run_main(monkeypatch, tmp_path / "nope.mp4") == 1
    assert "file not found" in capsys.readouterr().err


def test_main_image_post_skips_processing(tmp_path, monkeypatch, capsys, fake_run):
    photo = tmp_path / "p.JPG"
    photo.touch()
    assert run_main(monkeypatch, photo) == 0
    assert "IMAGE POST" in capsys.readouterr().out
    assert fake_run.calls == []


def test_main_video_report(tmp_path, monkeypatch, capsys, fake_run, fake_whisper):
    video = tmp_path / "v.mp4"
    video.touch()
    assert run_main(monkeypatch, video, "--frames", "2") == 0
    out = capsys.readouterr().out
    assert "DURATION: 30s" in out
    assert "Open n8n" in out
    assert out.count(".frame-") == 2
