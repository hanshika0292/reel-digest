"""Render a digest's Markdown into a standalone HTML page next to it (same name, .html).

Usage: render_digest.py digests/2026-10-20.md

Raw HTML in the Markdown is escaped, not rendered, because digests quote captions written by strangers.
"""

import html
import sys
from pathlib import Path

from markdown_it import MarkdownIt

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #faf9f6; --text: #1d1d1f; --muted: #6e6e73; --accent: #c2410c;
    --card: #ffffff; --border: #e5e2dc; --code-bg: #f2efe9;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #161616; --text: #ececec; --muted: #9a9a9a; --accent: #fb923c;
      --card: #1f1f1f; --border: #333; --code-bg: #262626;
    }}
  }}
  body {{
    background: var(--bg); color: var(--text); margin: 0;
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  main {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 80px; }}
  h1 {{ font-size: 28px; margin: 0 0 8px; }}
  h2 {{ font-size: 21px; margin: 40px 0 12px; padding-top: 16px; border-top: 1px solid var(--border); }}
  h3 {{ font-size: 17px; margin: 28px 0 6px; }}
  a {{ color: var(--accent); }}
  blockquote {{ margin: 12px 0; padding: 8px 14px; background: var(--card); border-left: 3px solid var(--accent);
    border-radius: 6px; color: var(--muted); }}
  blockquote p {{ margin: 0; }}
  code {{ background: var(--code-bg); padding: 1px 5px; border-radius: 4px; font-size: 0.88em; }}
  pre {{ background: var(--code-bg); padding: 14px; border-radius: 8px; overflow-x: auto;
    border: 1px solid var(--border); font-size: 13px; line-height: 1.5; }}
  pre code {{ background: none; padding: 0; }}
  li {{ margin: 3px 0; }}
  img {{ width: 240px; max-width: 100%; border-radius: 8px; border: 1px solid var(--border);
    margin: 8px 8px 0 0; vertical-align: top; cursor: zoom-in; }}
  img.zoomed {{ width: 100%; max-width: 560px; cursor: zoom-out; }}
</style>
</head>
<body>
<main>
{body}
</main>
<script>
  document.querySelectorAll("img").forEach(img => img.addEventListener("click", () => img.classList.toggle("zoomed")));
  // Repo, plugin and tool links open in a new tab so the digest stays open
  document.querySelectorAll("a[href^='http']").forEach(a => {{ a.target = "_blank"; a.rel = "noopener noreferrer"; }});
</script>
</body>
</html>
"""


def main() -> int:
    src = Path(sys.argv[1]).resolve()
    text = src.read_text()
    md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), src.stem)
    out = src.with_suffix(".html")
    out.write_text(PAGE.format(title=html.escape(title), body=md.render(text)))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
