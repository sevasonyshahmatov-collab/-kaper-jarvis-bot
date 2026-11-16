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
Порядок важен (проверка безопасности 16.11): сначала домен подтверждается за нашим аккаунтом GitHub и привязывается к сайту,
и только потом — записи DNS. Если сделать DNS раньше, в промежутке домен может привязать к своему сайту чужой аккаунт GitHub.

1. **Подтвердить домен в аккаунте GitHub**: Settings аккаунта → Pages → Add a domain → `домен.ru`; GitHub даст TXT-запись
   `_github-pages-challenge-<аккаунт>` — внести её у регистратора, нажать Verify. Запись **не удалять никогда**.
2. **Привязать домен к сайту**: в репозитории сайта (`sevasonyshahmatov-collab/sevasonyshahmatov-collab.github.io`)
   Settings → Pages → Custom domain → `домен.ru`. GitHub сам положит файл `CNAME` в корень репозитория сайта;
   `publish_root.sh` его не трогает (явно пропускает `CNAME`). В `team/site/v3a` файл `CNAME` **не добавлять**.
3. **DNS у регистратора** (только после 1–2): для `домен.ru` — четыре записи A (185.199.108.153, 185.199.109.153,
   185.199.110.153, 185.199.111.153) и четыре AAAA (2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153,
   2606:50c0:8003::153); для `www` — CNAME на `sevasonyshahmatov-collab.github.io`. Записи `*` (на все поддомены) **не делать**.
4. **HTTPS**: дождаться сертификата (до суток), включить «Enforce HTTPS» в Settings → Pages.
5. **Защита почты домена** (почты на домене пока нет — запрещаем отправку писем от его имени):
   `@ TXT "v=spf1 -all"`, `_dmarc TXT "v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s"`, `@ CAA 0 issue "letsencrypt.org"`.
   Когда появится почта (например, Яндекс 360) — SPF и DMARC заменить на записи почтового сервиса.
6. **Адрес сайта**: `SITE_ORIGIN = 'https://домен.ru'` в `seo/seo_config.py` (или `SITE_ORIGIN` в окружении
   `site-v3a-daily.yml`). `PUBLIC_ORIGIN` сам станет тем же. Запуск `python3 team/site/v3a/seo/build_seo.py` — canonical, og:url,
   JSON-LD, sitemap на новый адрес. Проверить, что не осталось ни заглушки, ни старого адреса:
   `grep -rlE 'jarvibet\.example|sevasonyshahmatov-collab\.github\.io' team/site/v3a --include=*.html | grep -v 'proto\|concepts\|preview'` — пусто
   (16.11 старый адрес вписан в `index.html`, `matches.html`, `results.html`, `forecast.html`, `model.html`, `glossary.html` и страницы матчей).
   После этого — «сообщить о подделке» в подвале (`assets/footer.js`, `.jvf-fake`), когда будет адрес почты.
7. **Открыть для поиска**: `INDEXING_OPEN = True` (или `SITE_INDEXING_OPEN=1`) и снова `build_seo.py` — уходит noindex со страниц,
   robots.txt разрешает обход и указывает на sitemap.xml.
8. **Публикация robots / sitemap** (правка `daily/publish_new.sh` и `publish_root.sh` — нужна отдельная «да»):
   убрать из исключений `/robots.txt`, `/sitemap.xml`; в `publish_root.sh` разрешить перезаписать эти два файла старого сайта
   (как index.html и 404.html). Иначе останутся robots/sitemap старого сайта. 404.html новая — публикуется с 13.11.
9. **Старый сайт**: /prognozy/, /app/, /stats/, /trendy/, /old/ — закрыть от поиска (noindex или Disallow в новом robots.txt),
   чтобы не мешали новым страницам; мини-приложение /app/ — проверить, что Telegram открывает его по новому адресу
   (адрес WebApp в настройках бота).
10. **Переадресации** /new/… и папок лиг уже с noindex — оставить.
11. **Поисковики**: Яндекс Вебмастер и Google Search Console — подтвердить домен (meta-тег или DNS TXT), отправить sitemap.xml.
12. **Проверка после**: превью ссылки в Telegram (главная, клуб, матч), https без предупреждений, `/khl/` → страница лиги,
   несуществующий адрес → наша 404, `robots.txt` и `sitemap.xml` открываются.

Не делать: canonical на github.io; открывать индексацию до домена.
