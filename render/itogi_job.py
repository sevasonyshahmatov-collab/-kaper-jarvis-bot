"""Постеры «Итоги дня» и «Матчи дня» по данным таблицы → в Telegram (запускается GitHub Actions, .github/workflows/itogi.yml).

Таблица (Apps Script) после последнего матча дня шлёт в GitHub событие «itogi» с данными:
    {"league": "KHL" | "NHL", "day": "2026-09-30", "date_title": "среда, 30 сентября", "chat": "<id>",
     "items": [{"home": "Амур", "away": "Нефтехимик", "sh": 1, "sa": 0, "mark": "" | "ОТ" | "Б" | "ОТ/Б"}]}
Рисуем формат «Ячейки» (results_ice2, variant 10) и отправляем фото в чат chat ботом TG_BOT_TOKEN (секрет репозитория).

«Матчи дня» — то же с "kind": "matchi" (событие «matchi»), в items вместо счёта время и линия в основное время:
    {"home": "Спартак", "away": "Трактор", "time": "19:30", "odds": [1.84, 4.37, 3.91] | null}
Рисуем формат «Колонки» (preview_ice, style='columns').
"extra" (необязательно, HTML) — дописывается к подписи: у НХЛ это «🇷🇺 Наши» (результативность россиян).
Не влезает в лимит подписи Telegram (1024 знака) — уходит отдельным сообщением сразу после фото.
"chats" — куда отправить (канал и группа у автоматики, ваш чат у кнопок); нет — "chat".
Картинка не нарисовалась — в те же чаты уходит подпись текстом (итоги не пропадут), задание помечается ошибкой.
Без TG_BOT_TOKEN — только сохраняем картинку (для проверки: python render/itogi_job.py payload.json).
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MARKS = {'', 'ОТ', 'Б', 'ОТ/Б'}
# подписи — без эмодзи: анимированные (премиум) бот в канал поставить не может, а обычные решили не ставить
LEAGUE_TITLE = {'KHL': '<b>КХЛ · итоги дня</b>', 'NHL': '<b>НХЛ · итоги ночи</b>'}
MATCHI_TITLE = {'KHL': '<b>КХЛ · матчи дня</b>', 'NHL': '<b>НХЛ · матчи дня</b>'}
EMOJI = re.compile('(?:[\U0001F1E6-\U0001F1FF]|[\U0001F000-\U0001FAFF]|[\u2600-\u27BF]|[\u2B00-\u2BFF]|\uFE0F|\u200D)+ ?')


def no_emoji(text):
    return re.sub(r'(?m)^[ \t]+', '', EMOJI.sub('', text))


def load_payload():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as f:
            return json.load(f)
    raw = os.environ.get('PAYLOAD') or ''
    if not raw.strip() or raw.strip() == 'null':
        raw = os.environ.get('INPUT_PAYLOAD') or '{}'
    return json.loads(raw)


def clean(payload):
    league = str(payload.get('league', '')).upper()
    if league not in LEAGUE_TITLE:
        raise SystemExit('неизвестная лига: %r' % league)
    items = []
    for it in payload.get('items') or []:
        home, away = str(it.get('home', '')).strip(), str(it.get('away', '')).strip()
        try:
            sh, sa = int(it.get('sh')), int(it.get('sa'))
        except (TypeError, ValueError):
            continue
        mark = str(it.get('mark') or '').strip()
        if home and away:
            items.append(dict(home=home, away=away, sh=sh, sa=sa, mark=mark if mark in MARKS else ''))
    if not items:
        raise SystemExit('в данных нет ни одного сыгранного матча')
    return league, items, str(payload.get('date_title') or '').strip(), str(payload.get('chat') or '').strip()


def clean_matchi(payload):
    league = str(payload.get('league', '')).upper()
    if league not in MATCHI_TITLE:
        raise SystemExit('неизвестная лига: %r' % league)
    items = []
    for it in payload.get('items') or []:
        home, away = str(it.get('home', '')).strip(), str(it.get('away', '')).strip()
        if not home or not away:
            continue
        odds = it.get('odds')
        try:
            odds = tuple(float(x) for x in odds) if odds and len(odds) == 3 and all(float(x) > 1 for x in odds) else None
        except (TypeError, ValueError):
            odds = None
        items.append(dict(home=home, away=away, time=str(it.get('time') or '').strip()[:5], odds=odds))
    if not items:
        raise SystemExit('в данных нет ни одного матча')
    return league, items, str(payload.get('date_title') or '').strip(), str(payload.get('chat') or '').strip()


def caption_matchi(league, items, date_title):
    """«02:30 | Филадельфия — Питтсбург» по строке на матч и «Время московское.» (как в канале)."""
    lines = ['%s%s — %s' % (html.escape(i['time']) + ' | ' if i['time'] else '', html.escape(i['home']), html.escape(i['away']))
             for i in items]
    return '\n'.join(lines) + '\n\nВремя московское.'


def caption(league, items, date_title):
    lines = ['%s — %s <b>%d:%d</b>%s' % (html.escape(i['home']), html.escape(i['away']), i['sh'], i['sa'],
                                          ' ' + i['mark'] if i['mark'] else '') for i in items]
    head = LEAGUE_TITLE[league] + (' · ' + html.escape(date_title) if date_title else '')
    return head + '\n\n' + '\n'.join(lines)


CAPTION_MAX = 1024


def send_message(token, chat, text):
    import requests
    r = requests.post('https://api.telegram.org/bot%s/sendMessage' % token, timeout=60,
                      data={'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'})
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


def send_photo(token, chat, path, text):
    import requests
    with open(path, 'rb') as f:
        r = requests.post('https://api.telegram.org/bot%s/sendPhoto' % token, timeout=60,
                          data={'chat_id': chat, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': f})
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


def main():
    payload = load_payload()
    kind = str(payload.get('kind') or os.environ.get('EVENT_KIND') or 'itogi').lower()
    league, items, date_title, chat = (clean_matchi if kind == 'matchi' else clean)(payload)
    # куда: список chats (канал и группа — автоматика, или ваш чат — кнопки меню); старые события — один chat
    chats = [str(c).strip() for c in (payload.get('chats') or [chat]) if str(c or '').strip()]
    # подпись — до рисования: если картинка не получится, её же опубликуем текстом
    if kind == 'matchi':
        text = str(payload.get('caption') or '').strip()[:1000] or caption_matchi(league, items, date_title)
    else:
        text = caption(league, items, date_title)
    extra = str(payload.get('extra') or '').strip()[:3500] if kind != 'matchi' else ''
    after = ''
    if extra:
        if len(text) + 2 + len(extra) <= CAPTION_MAX:
            text += '\n\n' + extra
        else:
            after = extra
    text, after = no_emoji(text), no_emoji(after)
    print('подпись:\n' + text + ('\n--- отдельным сообщением:\n' + after if after else ''))

    out = os.path.join(os.getcwd(), '%s_%s.jpg' % (kind, league.lower()))
    drawn = True
    try:
        if league == 'NHL':
            import nhl
            nhl.register()
        if kind == 'matchi':
            import preview_ice as pv
            pv.render(items, out, style='columns', league=league, date_title=date_title or None)
        else:
            import results_ice2 as ri
            ri.render(items, out, variant=10, league=league, date_title=date_title or None)
        print('нарисовано:', out, '— матчей', len(items))
    except Exception as e:                      # noqa: BLE001 — любая ошибка рисования: публикуем текст
        drawn = False
        print('картинка не нарисовалась:', repr(e))

    token = os.environ.get('TG_BOT_TOKEN')
    if not token:
        print('TG_BOT_TOKEN не задан — в Telegram ничего не отправлено')
        return
    if not chats:
        raise SystemExit('не указан чат (chat / chats) для отправки')
    errors = []
    for c in chats:
        try:
            if drawn:
                send_photo(token, c, out, text)
                if after:
                    send_message(token, c, after)
            else:
                send_message(token, c, text + ('\n\n' + after if after else ''))
            print('отправлено в', c)
        except SystemExit as e:
            errors.append('%s: %s' % (c, e))
    if errors or not drawn:
        raise SystemExit('; '.join(errors) or 'картинка не нарисовалась — опубликован текст')


if __name__ == '__main__':
    main()
