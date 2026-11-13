#!/usr/bin/env bash
# Обновить папку new/ в репозитории сайта из team/site/v3a (владелец 13.11: новый сайт рядом со старым, обновляется сам).
# Запуск: publish_new.sh <папка макета v3a> <папка new/ в копии репозитория сайта>
# Удаляет лишнее только внутри new/; остальной сайт не трогает. Рабочие снимки (shots/, shots_*/) и пробные видео
# не публикуются — на них не ссылается ни одна страница (владелец 13.11: «если нужно» — да). Список исключений — docs/handoff/SITE_V3A_NEXT_1311.md.
set -euo pipefail
src="${1%/}"; dst="${2%/}"
[ -f "$src/index.html" ] || { echo "нет макета: $src"; exit 1; }
case "$dst" in */new) ;; *) echo "папка назначения должна оканчиваться на /new: $dst"; exit 1;; esac
mkdir -p "$dst"
rsync -a --delete --delete-excluded \
  --exclude='*.py' --exclude='*.gz' --exclude='*probe*' --exclude='*_run.txt' --exclude='run.txt' --exclude='*.md' --exclude='__pycache__/' \
  --exclude='shots/' --exclude='shots_*/' --exclude='/assets/herobg/video/' --exclude='/assets/leaguecards/video/' \
  --include='/proto/' --include='/proto/home/' \
  --include='/proto/home/cards/***' --include='/proto/home/cosmos/***' --include='/proto/home/merge/***' \
  --include='/proto/home/players/***' --include='/proto/home/common.js' \
  --exclude='/proto/home/*' --exclude='/proto/*' \
  --exclude='/preview/' --exclude='/concepts/' --exclude='/daily/' --exclude='/seo/' \
  --exclude='/index-old.html' --exclude='/assets/herovid/src/' \
  --exclude='/robots.txt' --exclude='/sitemap.xml' --exclude='/404.html' \
  "$src/" "$dst/"
echo "new/: $(find "$dst" -type f | wc -l) файлов, $(du -sm "$dst" | cut -f1) МБ"
