# Third-party notices

Reel Digest contains no third-party code. Nothing below is copied into this repository: each component is
installed separately (cloned, or downloaded by `uv` or at first run) under its own license.

| Component | Used for | How it's installed | License |
|---|---|---|---|
| [instagram_dm_mcp](https://github.com/hanshika0292/instagram_dm_mcp), a fork of [trypeggy/instagram_dm_mcp](https://github.com/trypeggy/instagram_dm_mcp) | MCP server that reads the Instagram DM group | `git clone` into `instagram_dm_mcp/` (gitignored) | MIT, Copyright (c) 2025 Gala Labs Inc |
| [instagrapi](https://github.com/subzeroid/instagrapi) | Instagram private-API client used by the MCP server and `login_once.py` | dependency of instagram_dm_mcp | MIT, Copyright (c) 2023-2026 Mark Subzeroid and instagrapi contributors |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local speech-to-text in `tools/process_reel.py` | `uv sync --project tools` | MIT, Copyright (c) 2023 SYSTRAN |
| [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small) | Whisper `small` model weights (converted from [OpenAI Whisper](https://github.com/openai/whisper), MIT, Copyright (c) 2022 OpenAI) | downloaded on the first transcription | MIT |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | Markdown → HTML in `tools/render_digest.py` | `uv sync --project tools` | MIT, Copyright (c) 2020 ExecutableBookProject |
| [FFmpeg](https://ffmpeg.org) (`ffmpeg`, `ffprobe`) | Keyframes and video duration | installed by you (e.g. Homebrew) | LGPL/GPL, depending on the build |
| [Claude Code](https://github.com/anthropics/claude-code) | The agent that runs the digest | installed by you | Anthropic's terms |

Other Python packages come from PyPI through `uv` (see `tools/uv.lock`) under their own licenses.

Instagram is a trademark of Meta Platforms, Inc. Claude and Claude Code are trademarks of Anthropic, PBC. Reel
Digest is an independent project and is not affiliated with or endorsed by either company.
