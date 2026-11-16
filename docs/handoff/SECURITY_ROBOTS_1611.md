# Безопасность роботов — правки 16.11 (после проверки кода перед покупкой домена)

Разрешение владельца — «да» в чате аудита 16.11 (правки роботов публикации и утечки секретов, включая `main`).
Удаление веток, смену секретов и настройки GitHub делает сам владелец — ниже список.

## Что сделано (ветка `claude/security-main-1611` → `main`, коммит на пункт)
1. **Очередь Instagram** (`team/reels_daily/ig_queue.py`, `trusted()`): берёт артефакты `igq-*` только у запусков
   `reels-daily.yml` с событием `schedule` / `workflow_dispatch` / `repository_dispatch`, веткой `main` и репозиторием
   запуска = `GITHUB_REPOSITORY`. Остальные — строка «IGQ пропускаю запуск … не наш (…)» в журнале.
   Следствие: ручной запуск конвейера пушем `team/reels_daily/RUN` из ветки `claude/**` больше не попадает в очередь
   Instagram (ролик в Telegram и YouTube — как раньше). Для Instagram — запускать конвейер кнопкой Run workflow на `main`.
2. **Догрузка YouTube / пакет в Telegram** (`reels-retry.yml`): список запусков через `gh api …/runs?branch=main`,
   отбор в `jq` по событию, ветке и `head_repository.full_name`. Других мест, где роботы читают чужие запуски или
   качают артефакты по `run-id`, нет (`download-artifact` в `reels-daily.yml` — только своего запуска).
3. **Ввод в командах** (`reels-report.yml`): число дней — через `env: DAYS` и проверку `^[0-9]{1,3}$`. Все файлы
   `.github/workflows/` в `main` и в `claude/team-dev-site-v3a` пройдены: других `github.event.*` / `inputs.*` /
   `head_ref` / `ref_name` внутри `run:` нет.
4. **Ключи в журналах**: `instagram.clean()` вырезает `access_token=…` и `bot<ключ>` из текста ошибок — в
   `instagram.py`, `ig_queue.py`, `ig_mirror.py`, `report.py` (и в заметке «не загружен (…)»). Telegram: в
   `render/itogi_job.py`, `render/team_job.py`, `team/emoji/publish.py`, `tools/assets_fetch.py` запрос идёт через
   `_tg_post()` — ошибка связи без ключа в тексте. YouTube: ключи в заголовке и теле запроса, в адрес не попадают —
   правка не нужна. Заголовок `Authorization: Bearer` для Graph API не применяли — выбран вариант с вырезанием
   (поведение запросов не меняется).
5. **Копия истории сайта** (`site-history.yml`): в этот открытый репозиторий и в артефакт больше не кладётся. Нужны
   переменная `SITE_BACKUP_REPO` (владелец/имя, закрытый репозиторий) и секрет `SITE_BACKUP_TOKEN`; нет их или
   репозиторий не закрытый — запуск останавливается до чистки с понятным сообщением.
6. **Почта**: в `scrub_history.py` адрес — из секрета `SCRUB_OLD_MAIL` (пусто — почту не трогает). В
   `docs/handoff/HANDOFF_SITE_V2_3010.md` (ветка команды) — «аккаунт владельца». История не переписана: в старых
   коммитах адреса остаются.
7. **Роботы с правом записи** (`app-bg`, `app-probe`, `assets-fetch`, `months`, `team-emblems`, `tracks-intake`,
   `learn-weekly`): `persist-credentials: false`; ключ — только в шаге отправки (переменные `GIT_CONFIG_*` или
   `git -c …extraheader`). `permissions: contents: write` у всех уже явный и минимальный (все пушат).
8. **Ветка сайта `claude/team-dev-site-v3a`** (3 коммита): `site-v3a-daily.yml` — живой сайт только из этой ветки,
   ветка со словом `draft` (или `draft=yes` на ней) — в `draft/`, любая другая — никуда; `SITE_TOKEN` не на диске;
   `site.yml`, `site-check.yml` — как в `main`; `reels-report.yml` — как п. 3.

## Как проверено
Только чтением кода, `actionlint`, `pyflakes`, запуском функций на поддельных данных (отбор запусков в Python и `jq`,
проверка числа дней, вырезание ключей из настоящего текста ошибки `requests`, выбор цели публикации сайта по ветке,
заголовок git из окружения). Ни один рабочий процесс не запускался, боевые ключи не использовались.

## Посмотреть глазами первые запуски
- `ig-queue.yml` / тик соцсетей после ночного конвейера: ролики уходят, строк «пропускаю запуск» у своих запусков нет.
- `reels-retry.yml` 07:47 МСК: строки «запуск N: khl/nhl» есть.
- `site-v3a-daily.yml` (по cron из main): «публикация: live», сайт обновился.
- `learn-weekly.yml` в понедельник 07:17 МСК: коммит в ветку команды прошёл.
- При первом пуше `assets_run` / `tracks_inbox` / `BG_RUN` / `MONTHS_RUN` — что отправка в ветку прошла.

## Предложения (не сделано)
- Закрепить версии пакетов: `pip install requests numpy pillow cairosvg librosa rlottie-python brotli` без версий в
  `app-bg`, `app-probe`, `assets-fetch`, `months`, `team-emblems`, `learn-weekly`, `site-v3a-daily` — файла требований
  нет; завести `requirements-actions.txt` с точными версиями.
- Остальные старые копии процессов на ветке сайта (`reels-*`, `app-*`, …) отстают от `main`; по расписанию они там не
  работают, но вручную запускать их на этой ветке не стоит.

## Владельцу сделать самому
1. Удалить ветки `backup/site-history-20261103-0727`, `backup/site-history-20261105-0709` и артефакт `site-before-bundle`.
2. Settings → Actions → General → «Fork pull request workflows from outside collaborators» = «Require approval for all
   outside collaborators».
3. Защита ветки `main` (Settings → Branches).
4. Settings → Emails → «Keep my email addresses private» и «Block command line pushes that expose my email».
5. Двухэтапная защита на GitHub, Google, Telegram.
6. Проверить, удалён ли запуск № 83 (в журнале был старый ключ треков) и что `TRACKS_KEY` длинный и случайный.
7. Завести отдельный секрет `SITE_SEAL_KEY` (сейчас `site.yml` берёт `SITE_SEAL_KEY || SITE_TOKEN`; код не меняли —
   иначе запечатанные данные перестанут читаться; новый ключ — по согласованию, с перезапечатыванием).
8. Для будущей чистки истории — закрытый репозиторий для копии (`SITE_BACKUP_REPO`, `SITE_BACKUP_TOKEN`) и секрет
   `SCRUB_OLD_MAIL`.
