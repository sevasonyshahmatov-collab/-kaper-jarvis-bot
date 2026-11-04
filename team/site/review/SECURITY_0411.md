# Безопасность сайта v3a — проверка 04.11 (ночью)

Что проверяли: `team/site/v3a` (ветка `claude/team-dev-site-v3a`, 1289 файлов, 109 МБ), три workflow `site-v3a-*.yml` и `site-v3a-daily-cron.yml` из main, вся история папки (122 коммита, поиск по шаблонам секретов), Python-сборщики. Живые сервисы не трогали; страницы гоняли локально в Playwright (1440 px и iPhone 13). Значения секретов в отчёт не пишем. Прошлый аудит (боевой сайт, 03.11) — `team/site/security/AUDIT_2026-11-03.md`; его пункты про сырой план `data/khl-*.json` к макету v3a не относятся.

## Сводка

**Что опасно сейчас.** Ничего критичного. Секретов (токены, ключи, chat_id, e-mail, таблицы, пути сессий) ни в папке сайта, ни в её истории нет. Макет закрыт `noindex`. Живого XSS из адресной строки нет: `?team= ?q= ?id= ?lg= ?card= ?s= #hash` либо проверяются белым списком, либо экранируются. Но в 8 местах чужой текст из данных попадал в разметку без экранирования (время матча, название лиги, позиция игрока, тип окончания, форма за 10 игр, код клуба в `src`). Сейчас эти поля делает наш сборщик из фиксированных списков, поэтому эксплуатировать их можно только через взлом источника данных. 5 мест я закрыл, 3 лежат в файлах других агентов (раздел «Передать»).

**Сделать перед публикацией (обязательно).**
1. Не выкладывать в публичный репозиторий всю папку: в ней `preview/` (60 МБ скриншотов и видео), `concepts/` (черновики), все `.py`, `.gz`-выгрузки ESPN, `espn_summary_probe.json`, логи конвейера, `*_run.txt`. Готовая команда для публикации — ниже.
2. Решить вопрос с данными линий и вероятностей: публичный `data/lines.js`, `model.js`, `today.js` отдают кэфы букмекеров (источники подписаны «Фонбет», «Pinnacle») и вероятности модели на ближайшие 2 дня. Правило проекта: «прогнозы и кэфы — только владельцу, в канал никогда». Для сайта это решение владельца (и юридический вопрос по рекламе азартных игр — 38-ФЗ).
3. Заголовки безопасности: GitHub Pages их не умеет. Либо Cloudflare перед сайтом (бесплатно), либо принять риски и поставить `<meta>`-версию (раздел «Заголовки»).
4. Убрать зависимость от Google Fonts (IP посетителя уходит в Google — для 152-ФЗ это передача за границу) и подгрузки gsap с jsdelivr без SRI: скачать файлы и положить в `assets/vendor/`.
5. Когда будет домен — включить HTTPS-принудительно и HSTS (на Cloudflare одной галочкой).

**Позже.** Закрепить версии pip-пакетов и Actions по SHA; заменить inline `onerror=` на общий обработчик (тогда можно строгую CSP без `unsafe-hashes`); фото игроков с `assets.nhle.com` и `www.khl.ru` хранить у себя; уведомление о cookies — только когда подключат Метрику (раздел «Приватность»).

## Таблица находок

| # | Серьёзность | Где | Что и чем грозит | Исправление |
|---|---|---|---|---|
| 1 | Высоко (перед публикацией) | вся папка `v3a/` | В публикацию попадёт 109 МБ, из них служебное: `preview/` 60 МБ, `concepts/`, `.py` (внутренние пути, имена веток и источников), `football/data/raw.json.gz`, `lineups.json.gz`, `espn_summary_probe.json`, `elo_raw.json`, `headshots_skipped.json`, `data/daily_log.json`, `*_run.txt`, `*/README.md` | Публиковать из списка разрешённых файлов (команда ниже) |
| 2 | Средне (решение владельца) | `data/lines.js`, `data/model.js`, `data/today.js`, `*.json` | Кэфы букмекеров с названиями БК и вероятности модели на матчи, которые ещё не вышли в канал. Нарушает правило «кэфы — только владельцу». Скрейпинг линий Фонбет/Pinnacle — вопрос к их условиям | Решить, что показывать до матча. Технически: отдавать на сайт только матчи с постом в канале (как `channel_view` на боевом сайте) |
| 3 | Средне | `assets/team.js:185` (`T.l10s`), `:200` (`g.x`, `g.gf:g.ga`) | Форма за 10 игр и тип окончания матча вставляются в `innerHTML` без `esc()`. Если источник вернёт текст с `<img onerror>`, он выполнится у всех посетителей страницы клуба. Проверено подстановкой | `esc(T.l10s||…)`, `esc(g.x)`. Файл правит другой агент — передать |
| 4 | Средне | `assets/hockey-players.js:10,39` (`em(p.t)` → `src="…"`) | Код клуба `p.t` попадает в атрибут `src` без экранирования: подмена данных ломает атрибут и вставляет `onerror`. Проверено подстановкой | `esc(p.t)` внутри `em()`. Файл правит другой агент — передать |
| 5 | Средне | `hockey/index.html:307–472` | Время/дата матча (`m.t.slice(11)`, `data-t="${m.t}"`), счёт и тип окончания (`g.x`) шли в разметку без `esc()`. XSS при подмене данных | **Исправлено** |
| 6 | Средне | `assets/players.js:48` (футбол, страница сейчас скрыта) | Позиция игрока из ESPN (`AM-R`, `CF-L`) вставлялась без `esc()` — единственное поле, которое реально приходит от внешнего API напрямую | **Исправлено** |
| 7 | Низко | `assets/trends.js:253` | Названия лиг в плашках «матчей нет» без `esc()` | **Исправлено** |
| 8 | Низко | `assets/deck.js:29,138` | `m.lg` без экранирования в `src` логотипа и в `href` лиги | **Исправлено** (`esc`, `encodeURIComponent`) |
| 9 | Средне | `assets/titles.js:15` и `<link rel="preload">` в 8 страницах | gsap и SplitText грузятся с `cdn.jsdelivr.net/npm/gsap@3.13.0` без SRI и без `crossorigin`. Версия закреплена, но компрометация CDN/пакета = чужой код на всём сайте. Из облака jsdelivr закрыт, хэш посчитать не смог | Скачать два файла в `assets/vendor/` и грузить с домена (заодно быстрее и меньше третьих лиц). Либо `s.integrity='sha384-…'; s.crossOrigin='anonymous'` + такие же атрибуты у preload. Хэш: `curl -s URL \| openssl dgst -sha384 -binary \| openssl base64 -A` |
| 10 | Средне (приватность) | все страницы: `fonts.googleapis.com`, `fonts.gstatic.com` | Каждый посетитель отдаёт Google свой IP, браузер и страницу (Referer). Для 152-ФЗ — трансграничная передача; в Германии за такое штрафовали | Скачать шрифты (Fira Sans Extra Condensed, Literata, Inter, Roboto Condensed) в `assets/fonts/` и убрать preconnect |
| 11 | Низко-средне (приватность) | `hockey/index.html`, `assets/hockey-players.js`, `league-hockey.js`, `deck.js` и др.: `https://assets.nhle.com` (~2070 ссылок в данных), `https://www.khl.ru` (~1880), `commons.wikimedia.org` (`league-foot.js:142`) | Фото игроков и арен грузятся напрямую с чужих серверов: они видят IP и (по умолчанию) адрес страницы. Часть уже с `referrerpolicy="no-referrer"`, не все. Ещё — право на использование картинок и риск, что КХЛ/НХЛ закроют хотлинк | Скачать в `assets/ph/` при сборке или хотя бы добавить `referrerpolicy="no-referrer"` ко всем таким `<img>` |
| 12 | Низко | 11 мест `onerror="…"` в `deck.js` (5), `hockey-players.js` (3), `players.js`, `search.js`, `trends.js` | Inline-обработчики не дают включить строгую CSP | Один общий `document.addEventListener('error', …, true)` для `img` (код ниже) |
| 13 | Низко | `team/index.html:15,87`, `football/team.html:13,87` (`document.write` с `?id=`) | Параметр `id` вырезается регуляркой `[a-z0-9_]+` — инъекции нет. Но `document.write` блокирует разбор страницы | Оставить; при желании заменить на `createElement('script')` |
| 14 | Низко | `team.js:8` `D.teams[ID]`, `league-foot.js:8` `D.leagues[LG]`, `league-hockey.js:12`, `trends.js:201` `CFG.types[…]` | Ключи `?id=constructor` / `?lg=__proto__` находят свойства прототипа: страница падает с ошибкой JS (XSS нет, ломается только у самого открывшего) | `Object.hasOwn(D.teams, ID)` вместо `D.teams[ID]` |
| 15 | Низко | `.github/workflows/site-v3a-*.yml` | `pip install requests numpy brotli pillow`, `opencv-python-headless<5 rembg onnxruntime` без точных версий; `actions/*@v4/@v5` по тегу, не по SHA; `rembg` сам тянет модель u2net из интернета. Подмена пакета = выполнение кода с `contents: write` | Файл `requirements-site.txt` с `==`, Actions по SHA (Dependabot). Автоправку не делал: критичности нет, и сломать три рабочих конвейера не хотелось |
| 16 | Низко | `site-v3a-daily.yml`, `-headshots.yml`, `-players.yml` | `push` на любую `claude/team-dev-**` запускает конвейер с правом записи. Это вход только у тех, кто и так может писать в репозиторий; script injection нет (`github.event.*` в `run:` не используется, `GITHUB_REF_NAME` берётся из env в кавычках). `permissions` минимальные (`contents: write`; `actions: write` только в headshots для самозапуска) | Оставить. Защитить ветки правилами, если появятся посторонние участники |
| 17 | Низко | `site-v3a-daily-cron.yml` (main) | `permissions: actions: write`, запускает только `gh workflow run site-v3a-daily.yml --ref claude/team-dev-site-v3a`. Входных данных нет, токен — стандартный | Всё в порядке |
| 18 | Низко | `daily/run.py:79` | В коде зашито имя репозитория живого сайта (`…/…github.io`, аккаунт владельца на GitHub). После публикации `.py` не должны попасть на сайт (п. 1) | Исключить `.py` из публикации |
| 19 | Низко | `data/today.js`, `today.json` (`arena.phone`, `arena.website`) | Телефон и сайт арены из API КХЛ лежат в публичных данных, на страницах не используются; сайты арен с `http://` | Не копировать эти поля в `today.json` |
| 20 | Низко | `football/build_data.py:12` | `eval()` словаря `RU` из `render/football.py`. Файл свой, из репозитория, не из сети | Заменить на `ast.literal_eval` при случае (не менял: без файла в этой ветке не проверить равенство) |
| 21 | Низко | `daily/*.py`, `hockey/*_fetch.py`, `football/*_fetch.py` | Проверено: `requests` везде с `timeout`; нет `verify=False`, `pickle`, `yaml.load`, `shell=True`; `subprocess` со списком аргументов. Имена файлов из внешних данных: клубы — slug из `[a-z0-9_]`, хоккейные — фиксированная таблица; `ph/<id>.webp` брал id из ESPN без проверки | Теперь id только цифры, а `split.py` не пишет за пределы папки (**исправлено**) |
| 22 | Инфо | `target="_blank"` | Все ссылки с `rel="noopener"` (ссылки на `t.me`, Commons). Открытых редиректов нет. Ссылок на БК нет; название БК встречается как подпись источника линии (см. п. 2) | `noopener` достаточно: `Referrer-Policy` теперь не отдаёт путь |
| 23 | Инфо | `localStorage`/cookies | Cookies сайт не ставит. `localStorage`: только `search.js` (последние запросы поиска, у посетителя в браузере); `sessionStorage`: флаг анимации перехода (`v3a.js`). Счётчиков, форм, iframe, `postMessage` нет | Уведомление о cookies сейчас не нужно |

## Исправлено ночью

Коммиты в `claude/team-dev-site-v3a` (все страницы после каждой правки прогнаны в Playwright, 1440 и iPhone 13, 17 страниц × 2: ошибок JS нет, тексты и картинки на месте).

- `c01e528d3ca1b5cc5f830c201968fe40fc5869f2` — экранирование в `hockey/index.html` (время, дата, счёт, тип окончания, `data-t`), `trends.js` (названия лиг), `deck.js` (логотип и ссылка лиги), `players.js` (позиция); `split.py` не пишет вне папки макета; `players_headshots.py` принимает только числовые id.
- `409189ed5fb93e697534927b5e6e9e8f71322c14` — `<meta name="referrer" content="strict-origin-when-cross-origin">` на 22 страницах (кроме `model.html` и `hockey/player.html`, их правят другие).

Как проверяли: все JSON и data-JS при отдаче подменялись, в каждую строку с пробелом/кириллицей, а во втором проходе — в каждую строку добавлялся `"'><img src=x onerror=…>`; страницы обходили со скроллом и кликами по кнопкам/вкладкам. Сработавшее поле = место без экранирования. После правок остались только `team.js` (п. 3) и `hockey-players.js` (п. 4). Параметры URL: 15 страниц × 6 вредных значений (`<img src=x onerror=…>`, `"><svg onload=…>`, `javascript:…`, `../../x`, `__proto__`, `constructor`) × 3 способа (все параметры сразу `?team= ?q= ?id= ?lg= ?card= ?s= ?k= ?f= ?theme= ?ctx= …`, только `#hash`, оба вместе) + ввод тех же значений в строку поиска = 270 открытий. Результат: ни одного `alert`, ни одного выполненного `onerror`/`onload`, ни одного внедрённого элемента; `?id=../../x` и `?lg=javascript:` просто не находят клуб/лигу. Единственное — JS-ошибка при `__proto__` на `football/league.html`, `football/team.html`, `team/index.html` (п. 14, ломается только страница у того, кто сам открыл такую ссылку). Новые `hockey/player.html` и `model.html` в том же тесте чистые.

## Передать другим агентам и владельцу

- **Агенту footer/nav/head:** ничего критичного в `nav.js`, `footer*` не найдено (`esc()` на месте). В `<head>` добавить `Permissions-Policy` через meta нельзя (не работает) — только заголовком.
- **Агенту team/search/hockey-players:** п. 3 (`team.js:185,200`) и п. 4 (`hockey-players.js:10,39`); заодно п. 14 (`Object.hasOwn`).
- **Агенту player/model:** замечаний нет; `player.js` берёт `id` только цифрами и `lg` по белому списку — образец. Добавить `<meta name="referrer" …>` в `model.html` и `hockey/player.html`.
- **Владельцу:** п. 1 (что публиковать), п. 2 (кэфы и вероятности до выхода поста), п. 10–11 (шрифты и фото у себя), включить в GitHub «Keep my email private» (из прошлого аудита).

## Что публиковать (исключение служебного)

Если публикуют из этого же репозитория через отдельный шаг workflow, копировать так (из `team/site/v3a` в папку `dist/`):

```bash
rsync -a --prune-empty-dirs \
  --exclude='preview/' --exclude='concepts/' --exclude='daily/' --exclude='search/' --exclude='brand/' \
  --exclude='*.py' --exclude='*.md' --exclude='*_run.txt' --exclude='run.txt' --exclude='MONTHS_RUN' \
  --exclude='*.gz' --exclude='*.map' --exclude='*.bak' --exclude='.*' \
  --exclude='football/data/espn_summary_probe.json' --exclude='football/data/elo_raw.json' \
  --exclude='football/data/headshots_skipped.json' --exclude='football/data/slugs.json' \
  --exclude='data/daily_log.json' --exclude='assets/data/teams.json' --exclude='team/h2h.json' \
  team/site/v3a/ dist/
```

`brand/` — только скрипты сборки иконок (`icons_build.js`, `og_build.py`). Копии `data/*.json` рядом с `.js` (`football/data/football.json` и т. п.) страницы не грузят, их тоже можно не публиковать; а `hockey/data/nhl_players.json`, `khl_players.json`, `plite_*.json`, `team/season.json`, `football/data/photos.json`, `data/search.json` — нужны сайту (их грузят `fetch(`). После копирования прогнать на `dist/`: `grep -rE "(ghp_|github_pat_|AIza|sk-|BEGIN .*PRIVATE)" dist` и открыть главные страницы без ошибок.

## Заголовки и CSP

**GitHub Pages** не позволяет ставить заголовки. Через `<meta>` работают: `Content-Security-Policy` (без `frame-ancestors`), `referrer`. Не работают в `<meta>`: `frame-ancestors`, `X-Frame-Options`, `X-Content-Type-Options`, `Permissions-Policy`, HSTS. Защита от кликджекинга на Pages — только JS-обходом (ниже, слабее). Всё остальное даёт **Cloudflare** (бесплатный тариф, домен через него): правила Transform Rules → Modify Response Header, или файл `_headers` при хостинге на Cloudflare Pages/Netlify.

### Заголовки (Cloudflare / `_headers`)

```
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'sha256-…хэши inline-скриптов…'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https://assets.nhle.com https://www.khl.ru https://commons.wikimedia.org https://upload.wikimedia.org; media-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
  Referrer-Policy: strict-origin-when-cross-origin
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Cross-Origin-Opener-Policy: same-origin
```

Как собрана CSP (по реальным ресурсам): скрипты — свои и `cdn.jsdelivr.net` (gsap); inline-скрипты есть в 9 страницах (14 разных, первые строки тем/параметров), поэтому нужны их хэши (список ниже, пересчитывать при каждой правке `<head>`; подсчёт: `python3` с `sha256` по содержимому `<script>…</script>`). Стили: свои + Google Fonts, `'unsafe-inline'` нужен (149 `style="--c:…"` в разметке и сотни в JS). Картинки: свои, `data:` (SVG в CSS), NHL, КХЛ, Commons/upload.wikimedia (Special:FilePath перенаправляет на upload). Видео — свои (`assets/banners/*.mp4`). `connect-src 'self'`: сайт ходит только за своими JSON. Eval и `new Function` в коде нет.

Хэши inline-скриптов на момент проверки (`sha256-…`): `5af2Ny2/ClFZ2urReT2zrRab8IUCAdEXUlFJ7enScEU=` (concepts/home), `HrIi2BSPfo4orTg5AZNeODcYTw04mhEwWONytYksAyc=` (football/league), `nOelAyKZQADLtmB93tmxDpn+2wTIGK5lj5r4rNDQyu0=` (photo-credits), `zTZx/mgDRMKnRxz92VhpCpHc/urHVuT8y2FGkrvD/x4=`, `D5XTm8sgO1F31Fkycsqjvgdq0jVre/D+E1hxlCNbCh8=`, `2j3GnSUgywxWkAQ6Qx2bdCXca3/7rl1tojByVTeg+7I=` (football/team), `kbWFDBhmXoFeq/6G57U0Z+BZE+b77v4wdv+p578rXsQ=`, `pzsBzUihDEJEDn/uFFSqDYUHtKPwh8yR3hx2vVjPgz0=` (hockey/index), `o7K1fWGzP2PqDYbZcD5/C3NNNWYMVCqXnpYn+ocKLIw=` (hockey/league), `kq8STgFDeaxw6QkFBVaMty7mwZHix6IZqiEq3NzT9MQ=` (index), `pW6jg0MtVqNBY4lPr8nxrxROYEenIKzgJlSLwlg6exA=` (matches), `s4NrObsbbpCWAoC5CiaYJTLOxNacirtbCVyvLvUDOTE=`, `r/6thJ8mIjYSpUIfU2bwjC4CkoG4fc4+fQOJMF2ZORA=`, `iptYNcADuTCWLBi68ZEKj2WgDV15tuQR0pR6gaGu1Jg=` (team/index). Хэши дают смысл, только если скрипты не меняются; проще вынести все 14 в отдельные `.js` и убрать хэши.

**Что мешает строгой CSP, нужно сделать до включения:** (а) inline `onerror="…"` в 11 местах (п. 12) — заменить одним обработчиком:

```js
document.addEventListener('error',e=>{const t=e.target;if(t&&t.tagName==='IMG'&&t.dataset.onerr){/* 'remove' | 'ph' | 'text' */
  if(t.dataset.onerr==='remove')t.remove()}},true);
```
и в шаблонах писать `data-onerr="remove"` вместо `onerror="this.remove()"` (для `deck.js:30,345` с `replaceWith(...)` — вариант `ph`/`text` в том же обработчике); (б) `document.write` в 2 страницах разрешён хэшем скрипта, отдельно ничего не нужно.

### Вариант для GitHub Pages (в `<meta>`, без `frame-ancestors`)

Вставлять в `<head>` первым после `charset`, **только после** п. 12 и когда хэши совпадают (иначе сломает страницу, поэтому на страницы не ставил):

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'sha256-…'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https://assets.nhle.com https://www.khl.ru https://commons.wikimedia.org https://upload.wikimedia.org; media-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'">
```

Защита от встраивания в чужую страницу без заголовков (слабая, но лучше, чем ничего): в `<head>` до остальных стилей

```html
<style id="jv-fb">html{display:none}</style>
<script>if(top===self){document.getElementById('jv-fb').remove()}else{top.location=self.location}</script>
```
(скрипт тоже добавить в список хэшей). Если шрифты и gsap перенести к себе (п. 9–10), из CSP уходят `fonts.googleapis.com`, `fonts.gstatic.com`, `cdn.jsdelivr.net`, и политика становится почти `'self'`.

### Когда добавят Яндекс Метрику

Дополнения к CSP: `script-src … https://mc.yandex.ru https://mc.yandex.com https://yastatic.net`; `img-src … https://mc.yandex.ru https://mc.yandex.com`; `connect-src … https://mc.yandex.ru https://mc.yandex.com wss://mc.yandex.ru wss://mc.yandex.com`; при включённом Вебвизоре — `frame-src https://mc.yandex.ru`, `child-src blob:`. Сам код счётчика — inline, нужен его хэш (или вынести в файл). Метрика ставит cookies `_ym_*` и передаёт IP/устройство/страницы: нужны **уведомление о cookies с согласием до загрузки счётчика** (грузить скрипт только после «Принять»), политика обработки персональных данных на сайте и согласие по 152-ФЗ; вебвизор и карту кликов включать отдельно и осознанно (записывают действия посетителя). Параметры `?q=` и `#hash` не должны попадать в адрес страницы для Метрики (в поиске остаётся только локально).

## Чек-лист перед запуском живого сайта

- [ ] Публикуется только список из раздела «Что публиковать», `dist/` просмотрен глазами; `preview/`, `concepts/`, `*.py`, `*.gz` в нём нет.
- [ ] Решено, что делать с кэфами и вероятностями до выхода поста (п. 2); названия БК в подписях линий — согласованы.
- [ ] `grep` по `dist/` на `ghp_`, `github_pat_`, `AIza`, `sk-`, `PRIVATE KEY`, `chat_id`, `@gmail` — пусто.
- [ ] Правки п. 3, 4, 14 в `team.js` и `hockey-players.js` внесены (после агента, который их правит).
- [ ] Шрифты и gsap лежат у нас (или у gsap SRI); фото игроков — у нас либо `referrerpolicy="no-referrer"`.
- [ ] 11 inline `onerror` заменены; включена CSP (заголовком через Cloudflare или `<meta>`); в консоли ни одного нарушения CSP на 17 основных страницах.
- [ ] `Referrer-Policy`, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Permissions-Policy`, HSTS отдаются (проверка: `curl -sI https://домен/`).
- [ ] Включён HTTPS и редирект с http; для GitHub Pages — галочка «Enforce HTTPS».
- [ ] В GitHub владельца включено «Keep my email private» и «Block command line pushes that expose my email».
- [ ] В `requirements-site.txt` точные версии, Actions закреплены по SHA (Dependabot).
- [ ] В макете нет `robots.txt`, а страницы закрыты `noindex`: решить, когда снимать `noindex`, и добавить `robots.txt` и `sitemap.xml`.
- [ ] Если ставят Метрику: баннер cookies, согласие до загрузки, политика конфиденциальности, CSP дополнена.
