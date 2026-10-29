import sys

import pytest

import render_digest


def render(tmp_path, monkeypatch, text, name="2026-10-20.md"):
    src = tmp_path / name
    src.write_text(text)
    monkeypatch.setattr(sys, "argv", ["render_digest.py", str(src)])
    assert render_digest.main() == 0
    return src.with_suffix(".html").read_text()


def test_writes_html_next_to_markdown(tmp_path, monkeypatch, capsys):
    page = render(tmp_path, monkeypatch, "# Digest Oct 20\n\nHello **world**\n")
    assert "<title>Digest Oct 20</title>" in page
    assert "<strong>world</strong>" in page
    assert capsys.readouterr().out.strip().endswith("2026-10-20.html")


def test_title_falls_back_to_file_stem(tmp_path, monkeypatch):
    page = render(tmp_path, monkeypatch, "no heading here\n")
    assert "<title>2026-10-20</title>" in page


def test_raw_html_from_captions_is_escaped(tmp_path, monkeypatch):
    page = render(tmp_path, monkeypatch, "# T\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n")
    body = page.split("<main>")[1].split("</main>")[0]
    assert "<script>" not in body
    assert "<img src=x" not in body
    assert "&lt;script&gt;" in body


def test_title_is_escaped(tmp_path, monkeypatch):
    page = render(tmp_path, monkeypatch, "# <b>Bold</b> & co\n")
    assert "<title>&lt;b&gt;Bold&lt;/b&gt; &amp; co</title>" in page


@pytest.mark.parametrize("snippet, expected", [
    ("| a | b |\n|---|---|\n| 1 | 2 |\n", "<table>"),
    ("~~old~~\n", "<s>old</s>"),
])
def test_tables_and_strikethrough_enabled(tmp_path, monkeypatch, snippet, expected):
    assert expected in render(tmp_path, monkeypatch, "# T\n\n" + snippet)
