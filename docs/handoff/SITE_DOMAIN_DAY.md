# Сайт v3a: день покупки домена — что сделать (подготовлено 13.11, п. 8 списка; ничего не включено)

Сейчас: сайт в корне https://sevasonyshahmatov-collab.github.io/, для поиска закрыт (noindex на страницах, robots.txt и
sitemap.xml в репозитории сайта — старого сайта). canonical, og:url, JSON-LD и sitemap пишутся на заглушку
`https://jarvibet.example` — на github.io canonical не ставим. Картинки превью ссылок (og:image) — на github.io
(`PUBLIC_ORIGIN`), чтобы Telegram показывал их уже сейчас.

Всё про адрес и индексацию — в одном месте: `team/site/v3a/seo/seo_config.py` (или переменные окружения в Actions).
Готово к открытию: `team/site/v3a/robots.txt` и `sitemap.xml` (4,7 тыс. адресов: разделы, лиги, «Прогноз на сегодня»,
клубы /khl/ska/, свежие матчи, профили хоккеистов и футболистов, сравнения; без proto/preview/concepts), title и
description уникальны, на каждой странице один h1 — проверка `python3 team/site/v3a/seo/check_pages.py` (0 ошибок 13.11).

## По шагам (каждый — с «да» владельца)
1. **DNS** у регистратора: для `домен.ru` — четыре записи A на GitHub Pages (185.199.108.153, 185.199.109.153,
   185.199.110.153, 185.199.111.153); для `www` — CNAME на `sevasonyshahmatov-collab.github.io`.
2. **CNAME** — файл `CNAME` с одной строкой `домен.ru` в корне репозитория сайта
   (`sevasonyshahmatov-collab/sevasonyshahmatov-collab.github.io`); в настройках Pages — Custom domain, затем Enforce HTTPS
   (сертификат выпускается до суток). `publish_root.sh` чужие файлы не трогает — CNAME не пропадёт.
3. **Адрес сайта**: `SITE_ORIGIN = 'https://домен.ru'` в `seo/seo_config.py` (или `SITE_ORIGIN` в окружении
   `site-v3a-daily.yml`). `PUBLIC_ORIGIN` сам станет тем же. Запуск `python3 team/site/v3a/seo/build_seo.py` — canonical, og:url,
   JSON-LD, sitemap на новый адрес. Проверить: `grep -rl jarvibet.example team/site/v3a --include=*.html | grep -v proto` — пусто.
4. **Открыть для поиска**: `INDEXING_OPEN = True` (или `SITE_INDEXING_OPEN=1`) и снова `build_seo.py` — уходит noindex со страниц,
   robots.txt разрешает обход и указывает на sitemap.xml.
5. **Публикация robots / sitemap** (правка `daily/publish_new.sh` и `publish_root.sh` — нужна отдельная «да»):
   убрать из исключений `/robots.txt`, `/sitemap.xml`; в `publish_root.sh` разрешить перезаписать эти два файла старого сайта
   (как index.html и 404.html). Иначе останутся robots/sitemap старого сайта. 404.html новая — публикуется с 13.11.
6. **Старый сайт**: /prognozy/, /app/, /stats/, /trendy/, /old/ — закрыть от поиска (noindex или Disallow в новом robots.txt),
   чтобы не мешали новым страницам; мини-приложение /app/ — проверить, что Telegram открывает его по новому адресу
   (адрес WebApp в настройках бота).
7. **Переадресации** /new/… и папок лиг уже с noindex — оставить.
8. **Поисковики**: Яндекс Вебмастер и Google Search Console — подтвердить домен (meta-тег или DNS TXT), отправить sitemap.xml.
9. **Проверка после**: превью ссылки в Telegram (главная, клуб, матч), https без предупреждений, `/khl/` → страница лиги,
   несуществующий адрес → наша 404, `robots.txt` и `sitemap.xml` открываются.

Не делать: canonical на github.io; открывать индексацию до домена.
