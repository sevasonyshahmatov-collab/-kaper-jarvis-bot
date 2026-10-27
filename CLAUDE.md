# JARVIS — @jarvibet (прогнозы на хоккей КХЛ и НХЛ)

Этот файл читается в начале каждой сессии: здесь только главное и где искать остальное. Подробности — по ссылкам,
читать по необходимости (экономия токенов, `team/RULES.md`).

## Главное
- Пиши владельцу и в канал по-русски, коротко: что сделано, что получилось, что нужно от него.
- **Прогнозы и кэфы — только черновиками владельцу в бот, в канал никогда.** Ключи и токены не проси и не записывай.
- Ветка команды — `claude/project-migration-old-account-6e31vz`. В `main` — только через PR; вливает команда сама
  после проверок (разрешение владельца 26.10, `team/RULES.md` «Постоянные разрешения»).
  В `apps-script/` ветки команды не пушить: таблицы ставят код оттуда — правки бота через ветку `claude/team-dev-…` и PR.
- Сеть облачной сессии закрыта для сайтов лиг и Telegram: данные матчей и отправка владельцу — через GitHub Actions
  (`itogi.yml`, см. скилл `jarvis-send`).
- Владелец правит ставки в боте своими словами — итоги считать по фактической ставке (`team/INBOX.md`, «правка владельца
  в боте»), не по черновику.

## Где что
- Правила команды: `team/RULES.md`; порядок дня руководителя: `team/LEAD.md`; журнал: `team/LOG.md`; решения владельца
  от бота: `team/INBOX.md`; прогнозы: `team/picks/README.md`, история — `team/PICKS.md`.
- Итоги дня: `team/daily/` (`morning.py`, `ask.py`, `banner.py`); послематчевые посты: `team/postmatch/README.md`.
- Ролики: `render/reels/`, конвейер `team/reels_daily/`, правила роликов — `team/RULES.md` «Ролики».
- Сайт: `team/site/`, `docs/handoff/SITE.md`. Соцсети: `docs/handoff/SMM_AGENT.md`.
- Бот и таблицы (Apps Script): `apps-script/`, `docs/handoff/HANDOFF_CODE.md`; проверка без затрат — `tools/gas_mock/`.
- Передачи между сессиями: `docs/handoff/` (свежая — `HANDOFF_LEAD_2710.md`).

## Скиллы проекта (`.claude/skills/`)
- `jarvis-send` — отправить владельцу в Telegram сообщение, картинку, видео (задание для `itogi.yml`).
- `jarvis-postmatch` — послематчевый пост «Итог матча» по одной ставке.
- `jarvis-recap` — итоги дня с баннером по списку ставок владельца.
- `jarvis-picks` — ежедневные прогнозы КХЛ / НХЛ владельцу в бот (всегда Opus).
- `jarvis-troubleshoot` — «не пришло / сломалось»: памятка найденных причин и что делать.
- `jarvis-brief` — из короткой идеи владельца подробное ТЗ. **Новая идея в 1–2 фразы — сначала этот скилл, потом работа**
  (владелец 27.10).
- Модели (поле `model` в скилле): скиллы в своём окне (postmatch, recap, troubleshoot) — Sonnet, прогнозы — Opus.
  `jarvis-send` работает в основном чате — модель ему не задавать: смена модели сбрасывает кэш чата.

## Продвижение — какой скилл брать (владелец 26.10: «пользуемся всеми»)
- Instagram — `ig-*` (голос — `.claude/instagram/voice.md`). Любой текст перед показом — через `ig-human`.
  Данные профиля и постов — `team/social/ig_snapshot.py` через `itogi.yml` (метки IGSNAP_*), затем `ig-profile`, `ig-audit`.
- Сайт — плагины `searchfit-seo` (seo-audit, on-page-seo, schema-markup) и `copywriting-kit` (copy-diagnose, copy-edit).
- Посты, кампании, проверка тона — плагин `marketing` (content-creation, campaign-plan, brand-review по voice.md).
- YouTube — плагин `tubealfred-youtube` (нужна сеть к его серверу; из облака может быть закрыта). Картинки — `image-generation`.
- Дизайн картинок, слайдов, сайта (владелец 27.10) — скиллы `impeccable` (типографика, отступы, палитра; команды audit,
  critique, polish, bolder) и `emil-design-eng` (мелочи и полировка интерфейса). Вёрстка HTML → снимок Playwright
  (`require('playwright')`, пример — `team/out/2026-10-27/sheet_stories_html.py` + `shot.js`), результат смотреть глазами.
- Правила канала важнее советов скиллов: без БК, промокодов, гарантий, выдуманных цифр (`team/RULES.md`, voice.md).
