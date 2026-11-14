#!/usr/bin/env bash
# Черновик сайта для просмотра владельцем (задание 14.11): папка draft/ в репозитории сайта — из ветки-черновика.
# Собирается так же, как раньше new/ (publish_new.sh: те же исключения), запуск только вручную (site-v3a-daily.yml, draft=yes).
# Трогает ТОЛЬКО draft/: живые страницы в корне, old/, new/ и остальной сайт не меняются. Страницы — с noindex, как и весь новый сайт.
# 404.html не кладём: у неё <base href="/"> — она для корня. Убрать черновик: удалить папку draft/ в репозитории сайта.
# Запуск: publish_draft.sh <папка макета v3a> <папка draft/ в копии репозитория сайта>
set -euo pipefail
src="${1%/}"; dst="${2%/}"
case "$dst" in */draft) ;; *) echo "папка назначения должна оканчиваться на /draft: $dst"; exit 1;; esac
here="$(cd "$(dirname "$0")" && pwd)"
stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
bash "$here/publish_new.sh" "$src" "$stage/new" >/dev/null
rm -f "$stage/new/404.html"
mkdir -p "$dst"
rsync -a --delete "$stage/new/" "$dst/"
echo "draft/: $(find "$dst" -type f | wc -l) файлов, $(du -sm "$dst" | cut -f1) МБ"
