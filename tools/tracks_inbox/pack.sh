#!/usr/bin/env bash
# Запаковать mp3 открытым ключом ящика: tools/tracks_inbox/pack.sh <папка с <имя>.mp3>
# → tools/tracks_inbox/box/ (коммит и пуш запускают tracks-intake.yml; после приёма ящик из ветки убрать).
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
SRC="$1"
mkdir -p "$D/box"
P=$(mktemp)
openssl rand -hex 32 | tr -d '\n' > "$P"
openssl pkeyutl -encrypt -pubin -inkey "$D/inbox_pub.pem" -pkeyopt rsa_padding_mode:oaep -in "$P" -out "$D/box/batch.key"
for f in "$SRC"/*.mp3; do
  openssl enc -aes-256-cbc -pbkdf2 -pass "file:$P" -in "$f" -out "$D/box/$(basename "$f" .mp3).mp3.box"
done
shred -u "$P" 2>/dev/null || rm -f "$P"
ls "$D/box"
