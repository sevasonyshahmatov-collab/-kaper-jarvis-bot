---
name: jarvis-send
description: >-
  Отправить владельцу @jarvibet в Telegram текст, картинку, гифку или видео через GitHub Actions (itogi.yml):
  составить задание team/out/<день>/<имя>.json, закоммитить в ветку команды и запустить workflow. Использовать, когда
  нужно что-то прислать владельцу в бот (отчёт, черновик поста, ролик, баннер) — напрямую в Telegram из облака нельзя.
---

# jarvis-send

1. Задание — `team/out/<ГГГГ-ММ-ДД>/<имя>.json`:
   ```json
   {"day": "2026-10-26",
    "make": ["team/out/2026-10-26/<скрипт>.py"],
    "messages": [
      {"to": "owner", "type": "text", "text": "…"},
      {"to": "owner", "type": "photo", "files": ["out/…/x.jpg"], "text": "подпись", "html": true, "emoji": true,
       "buttons": "post", "pid": "2610-1"}]}
   ```
   - `type`: text, photo, animation (mp4-гифка), documents (каждое видео — отдельным сообщением: Telegram не принимает
     пакет больше ~50 МБ), poll. `make` — необязательно: скрипты, которые рисуют файлы до отправки (пути — от корня).
   - Кнопки «Опубликовать / Редактировать / Не надо» — `"buttons": "post"` и уникальный `pid` (ММДД-N). Подпись к фото
     и гифке — не длиннее 1024 знаков, текст — 4096.
   - Прогнозы и кэфы — только `"to": "owner"`, в канал сам бот публикует по кнопке владельца.
2. Коммит и пуш в ветку команды `claude/project-migration-old-account-6e31vz` (при отказе — `git pull --rebase` и снова).
3. Запуск: `mcp__github__actions_run_trigger` → `run_workflow`, `workflow_id: itogi.yml`,
   `ref: claude/project-migration-old-account-6e31vz`,
   `inputs: {"payload": "{\"kind\":\"team\",\"job\":\"team/out/<день>/<имя>.json\"}"}`.
4. Проверка: `actions_list` → последний запуск `itogi.yml`; `get_job_logs` с небольшим `tail_lines` — строки
   `→ owner · <тип> · …` значат, что ушло. Не опрашивать чаще раза в 20–30 с.
