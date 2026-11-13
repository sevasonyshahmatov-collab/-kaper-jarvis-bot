#!/usr/bin/env bash
# Новый сайт — главный (владелец 13.11: «новый сайт можно делать главным, для поиска пока не открывать»).
# Кладёт макет v3a в КОРЕНЬ репозитория сайта рядом со старым сайтом (prognozy/, app/, stats/, trendy/, data/*.json старого — не трогаем).
# Запуск: publish_root.sh <папка макета v3a> <копия репозитория сайта>
#  - список своих файлов — .v3a-files: удаляем только то, что сами клали раньше и чего больше нет в макете;
#  - чужой файл (старого сайта) с тем же путём не перезаписываем, кроме index.html (главная — теперь новая);
#  - .v3a-root — метка для site.yml: корневую index.html не заменять лендингом старого сайта (тот уходит в old/);
#  - страницы нового сайта остаются с noindex, robots.txt и sitemap.xml старого сайта не трогаем;
#  - прежняя папка new/ — короткая переадресация на главную.
set -euo pipefail
src="${1%/}"; dst="${2%/}"
[ -f "$src/index.html" ] || { echo "нет макета: $src"; exit 1; }
[ -d "$dst/.git" ] || { echo "нет копии репозитория сайта: $dst"; exit 1; }
here="$(cd "$(dirname "$0")" && pwd)"
stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
bash "$here/publish_new.sh" "$src" "$stage/new" >/dev/null
(cd "$stage/new" && find . -type f | sed 's#^\./##' | LC_ALL=C sort) > "$stage/files"
old_list="$dst/.v3a-files"; touch "$old_list"
# 1) удалить свои прежние файлы, которых больше нет
LC_ALL=C comm -23 <(LC_ALL=C sort -u "$old_list") "$stage/files" | while IFS= read -r f; do
  [ -n "$f" ] && rm -f "$dst/$f"
done
# 2) положить новые; чужие файлы не трогать (кроме index.html)
: > "$stage/mine"
skipped=0
while IFS= read -r f; do
  if [ -e "$dst/$f" ] && [ "$f" != index.html ] && ! grep -qxF "$f" "$old_list"; then
    echo "пропуск (файл старого сайта): $f"; skipped=$((skipped+1)); continue
  fi
  echo "$f" >> "$stage/mine"
done < "$stage/files"
rsync -a --files-from="$stage/mine" "$stage/new/" "$dst/"
cp "$stage/mine" "$old_list"
find "$dst" -type d -empty -not -path "$dst/.git*" -delete 2>/dev/null || true
touch "$dst/.v3a-root"
# 3) new/ → переадресация на главную
rm -rf "$dst/new"; mkdir -p "$dst/new"
cat > "$dst/new/index.html" <<'HTML'
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url=../"><title>JARVIS</title><link rel="canonical" href="../"></head>
<body><p>Новый сайт теперь на главной: <a href="../">открыть</a>.</p><script>location.replace('../'+location.search+location.hash)</script></body></html>
HTML
echo "корень: $(wc -l < "$old_list") файлов нового сайта, пропущено чужих: $skipped"
