#!/usr/bin/env bash
# Приём треков владельца в ветку треков без ключа в чате (запускает .github/workflows/tracks-intake.yml).
#  1) нет tools/tracks_inbox/inbox_pub.pem → создаёт пару RSA; открытый ключ и закрытый, зашифрованный TRACKS_KEY,
#     кладёт сюда же коммитом. Открытым ключом треки можно запаковать где угодно (pack.sh) — открыть может только Actions.
#  2) есть tools/tracks_inbox/box/*.mp3.box + batch.key → распаковывает, шифрует TRACKS_KEY (как owner_tracks.py)
#     в tracks/<имя>.mp3.enc ветки claude/team-dev-tracks-v2 и пушит туда.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
D=tools/tracks_inbox
TB=claude/team-dev-tracks-v2
export TRACKS_KEY="$(printf %s "${TRACKS_KEY:-}" | tr -d '[:space:]')"
[ -n "$TRACKS_KEY" ] || { echo "нет секрета TRACKS_KEY"; exit 1; }
git config user.name "github-actions[bot]"
git config user.email "41898+github-actions[bot]@users.noreply.github.com"
T=$(mktemp -d)
git fetch -q origin "$TB:refs/remotes/origin/$TB"
# проверка ключа на старом треке — чтобы не зашифровать новые не тем ключом
git show "origin/$TB:tracks/slx.mp3.enc" > "$T/slx.enc"
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:TRACKS_KEY -in "$T/slx.enc" -out "$T/slx.mp3" \
  || { echo "TRACKS_KEY не открывает старые треки"; exit 1; }
echo "ключ треков проверен"

if [ ! -f "$D/inbox_pub.pem" ]; then
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "$T/priv.pem" 2>/dev/null
  openssl pkey -in "$T/priv.pem" -pubout -out "$D/inbox_pub.pem"
  openssl enc -aes-256-cbc -pbkdf2 -pass env:TRACKS_KEY -in "$T/priv.pem" -out "$D/inbox_priv.pem.enc"
  git add "$D/inbox_pub.pem" "$D/inbox_priv.pem.enc"
  git commit -qm "Tracks inbox: public key for packing owner's tracks (private key sealed with TRACKS_KEY)"
  git push -q origin "HEAD:$GITHUB_REF_NAME"
  echo "ключ приёма создан"
  exit 0
fi

ls "$D"/box/*.mp3.box >/dev/null 2>&1 || { echo "в ящике пусто"; exit 0; }
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:TRACKS_KEY -in "$D/inbox_priv.pem.enc" -out "$T/priv.pem"
openssl pkeyutl -decrypt -inkey "$T/priv.pem" -pkeyopt rsa_padding_mode:oaep -in "$D/box/batch.key" -out "$T/batch.pass"
W=$(mktemp -d)
git worktree add -q "$W" "origin/$TB"
mkdir -p "$W/tracks"
names=()
for b in "$D"/box/*.mp3.box; do
  n=$(basename "$b" .mp3.box)
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$T/batch.pass" -in "$b" -out "$T/$n.mp3"
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$T/$n.mp3" >/dev/null   # это правда звук
  openssl enc -aes-256-cbc -pbkdf2 -pass env:TRACKS_KEY -in "$T/$n.mp3" -out "$W/tracks/$n.mp3.enc"
  rm -f "$T/$n.mp3"
  names+=("$n")
done
cd "$W"
git add tracks
git commit -qm "Encrypted owner's tracks: ${names[*]}"
git push -q origin "HEAD:$TB"
echo "в ветку треков добавлены: ${names[*]}"
