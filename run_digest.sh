#!/bin/zsh
# Morning reel → workflow digest. launchd runs this daily (com.reeldigest.morning.plist); you can also run it by hand.
#   ./run_digest.sh          run once for today (skips if today's digest already exists)
#   ./run_digest.sh --force  retry after a failed run
set -u
ROOT="${0:A:h}"
cd "$ROOT"
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

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

# Waking the laptop fires a missed 7:47 run immediately; give Wi-Fi up to 2 minutes to connect
for i in {1..24}; do
  curl -s -o /dev/null --max-time 5 https://www.instagram.com && break
  sleep 5
done

echo "$(date) starting digest" >> "$LOG"
# perl alarm = a 60-minute hard timeout (macOS has no `timeout`); link lookups made runs longer than the old 45
perl -e 'alarm shift; exec @ARGV' 3600 \
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
STATUS=$?
RESULT=$(grep -E '^(OK|ERROR):' "logs/$DATE.out" | tail -1)
echo "$(date) exit=$STATUS result=${RESULT:-<none>}" >> "$LOG"

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
  notify "Reel digest problem" "${RESULT:-claude exited with $STATUS, see logs/$DATE.log}"
fi

# Downloads from failed runs are kept briefly so a --force retry can reuse their transcripts
find media -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null
exit $STATUS
