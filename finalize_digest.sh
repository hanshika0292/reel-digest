#!/bin/zsh
# Keep only what a digest needs: copy the images it embeds from media/<date>/ into digests/img/<date>/,
# repoint its links, then delete that day's downloads (videos, transcripts, unused frames).
#   ./finalize_digest.sh 2026-10-20
set -eu
ROOT="${0:A:h}"
cd "$ROOT"
DATE=$1
DIGEST="digests/$DATE.md"
[[ -f $DIGEST ]] || { echo "finalize: no $DIGEST, keeping media/$DATE"; exit 1; }
[[ -d media/$DATE ]] || exit 0

# Links may be relative (../media/...) or absolute ($ROOT/media/...)
grep -oE "(\.\./|$ROOT/)media/$DATE/[^)[:space:]]+\.(jpg|jpeg|png|webp)" "$DIGEST" | sort -u | while read -r ref; do
  src="media/$DATE/${ref##*/}"
  [[ -f $src ]] || continue
  mkdir -p "digests/img/$DATE"
  cp "$src" "digests/img/$DATE/"
done
sed -i '' -e "s|$ROOT/media/$DATE/|img/$DATE/|g" -e "s|\.\./media/$DATE/|img/$DATE/|g" "$DIGEST"

kept=$(ls "digests/img/$DATE" 2>/dev/null | wc -l | tr -d ' ')
rm -rf "media/$DATE"
echo "finalize: kept $kept images in digests/img/$DATE, deleted media/$DATE"
