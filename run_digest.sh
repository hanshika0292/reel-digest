#!/bin/zsh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Hanshika Gupta. See LICENSE.
# Morning reel → workflow digest. launchd runs this daily (com.reeldigest.morning.plist); you can also run it by hand.
#   ./run_digest.sh          run once for today (skips if today's digest already exists)
#   ./run_digest.sh --force  retry after a failed run
set -u
ROOT="${0:A:h}"
cd "$ROOT"
# Homebrew on Apple silicon first, then ~/.local/bin (uv's installer) and Intel Homebrew
export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Don't start in a lid-closed "dark wake"; wait until someone is at the Mac (see wait_for_user.zsh)
source "$ROOT/wait_for_user.zsh"
wait_for_user

DATE=$(date +%F)
mkdir -p digests media logs
LOG="logs/$DATE.log"

notify() {
  local msg=${2//\"/\'}
  osascript -e "display notification \"$msg\" with title \"$1\" sound name \"Glass\"" >/dev/null 2>&1
}

if [[ -f "digests/$DATE.md" && "${1:-}" != "--force" ]]; then
  echo "$(date) digest for $DATE already exists, skipping" >> "$LOG"
  exit 0
fi

IG_USER=$(grep -E '^INSTAGRAM_USERNAME=' instagram_dm_mcp/.env 2>/dev/null | cut -d= -f2-)
if [[ -z "$IG_USER" || ! -f "instagram_dm_mcp/${IG_USER}_session.json" || ! -f config.json ]]; then
  notify "Reel digest: setup needed" "Run ./login_once.py in $ROOT"
  echo "$(date) missing .env, session or config.json; run login_once.py" >> "$LOG"
  exit 1
fi

PROMPT=$(sed -e "s|{{DATE}}|$DATE|g" -e "s|{{ROOT}}|$ROOT|g" DIGEST_PROMPT.md)

run_claude() {
  # perl alarm = a 60-minute hard timeout (macOS has no `timeout`).
  # caffeinate stops idle sleep mid-run (it can't stop sleep when the lid is closed on battery; the retry covers that).
  caffeinate -i perl -e 'alarm shift; exec @ARGV' 3600 \
    claude -p "$PROMPT" \
      --mcp-config .mcp.json --strict-mcp-config \
      --allowedTools \
        "mcp__instagram_dms__list_messages_compact" \
        "mcp__instagram_dms__download_shared_post_from_message" \
        "Read" "Glob" "Grep" "WebSearch" "WebFetch" \
        "Edit(./digests/**)" "Edit(./state.json)" "Edit(./backlog.md)" \
        "Bash(uv run --project tools python tools/process_reel.py:*)" \
      --disallowedTools \
        "mcp__instagram_dms__send_message" "mcp__instagram_dms__send_photo_message" \
        "mcp__instagram_dms__send_video_message" "mcp__instagram_dms__delete_message" \
        "mcp__instagram_dms__like_media" "mcp__instagram_dms__mute_conversation" \
        "mcp__instagram_dms__mark_message_seen" \
    > "logs/$DATE.out" 2>> "$LOG"
}

# Two attempts: if the first fails (e.g. the lid was closed mid-run), wait until someone is at the Mac again and
# retry once. An expired Instagram session isn't retried; that needs ./login_once.py.
for ATTEMPT in 1 2; do
  if (( ATTEMPT == 2 )); then
    echo "$(date) retrying once when the Mac is in use again" >> "$LOG"
    [[ -f "digests/$DATE.md" ]] && mv "digests/$DATE.md" "logs/$DATE.failed-1.md"
    sleep 300
    wait_for_user
  fi
  # Waking the laptop can start a run before Wi-Fi is back; give it up to 2 minutes to connect
  for i in {1..24}; do
    curl -s -o /dev/null --max-time 5 https://www.instagram.com && break
    sleep 5
  done
  echo "$(date) starting digest (attempt $ATTEMPT)" >> "$LOG"
  run_claude
  STATUS=$?
  RESULT=$(grep -E '^(OK|ERROR):' "logs/$DATE.out" | tail -1)
  echo "$(date) exit=$STATUS result=${RESULT:-<none>}" >> "$LOG"
  [[ $STATUS -eq 0 && "$RESULT" == OK:* ]] && break
  [[ "$RESULT" == *"session expired"* ]] && break
done

if [[ $STATUS -eq 0 && "$RESULT" == OK:* ]]; then
  # Keep the digest and the images it embeds; delete today's videos, transcripts and unused frames
  ./finalize_digest.sh "$DATE" >> "$LOG" 2>&1
  uv run --project tools python tools/render_digest.py "digests/$DATE.md" >> "$LOG" 2>&1
  ln -sf "$DATE.md" digests/latest.md
  ln -sf "$DATE.html" digests/latest.html
  notify "☀️ Reel digest ready" "${RESULT#OK: }"
  # Opens in the default browser; set "open_report": false in config.json to only get the notification
  grep -qE '"open_report": *false' config.json || open "digests/$DATE.html"
else
  REASON="${RESULT:-claude exited with $STATUS}"
  notify "Reel digest problem" "${REASON}; see logs/$DATE.log"
  # A failed run's digest would make the next login skip today; move it aside so that run retries
  [[ -f "digests/$DATE.md" ]] && mv "digests/$DATE.md" "logs/$DATE.failed.md"
fi

# Downloads from failed runs are kept briefly so a --force retry can reuse their transcripts
find media -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null
exit $STATUS
