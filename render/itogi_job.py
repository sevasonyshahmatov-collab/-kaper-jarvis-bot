"""Постер «Итоги дня» по счёту из таблицы → в Telegram (запускается GitHub Actions, .github/workflows/itogi.yml).

Таблица (Apps Script) после последнего матча дня шлёт в GitHub событие «itogi» с данными:
    {"league": "KHL" | "NHL", "day": "2026-09-30", "date_title": "среда, 30 сентября", "chat": "<id>",
     "items": [{"home": "Амур", "away": "Нефтехимик", "sh": 1, "sa": 0, "mark": "" | "ОТ" | "Б" | "ОТ/Б"}]}
Рисуем формат «Ячейки» (results_ice2, variant 10) и отправляем фото в чат chat ботом TG_BOT_TOKEN (секрет репозитория).
Без TG_BOT_TOKEN — только сохраняем картинку (для проверки: python render/itogi_job.py payload.json).
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MARKS = {'', 'ОТ', 'Б', 'ОТ/Б'}
LEAGUE_TITLE = {'KHL': '🏒 <b>КХЛ · итоги дня</b>', 'NHL': '🇺🇸 <b>НХЛ · итоги ночи</b>'}


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


def caption(league, items, date_title):
    lines = ['%s — %s <b>%d:%d</b>%s' % (html.escape(i['home']), html.escape(i['away']), i['sh'], i['sa'],
                                          ' ' + i['mark'] if i['mark'] else '') for i in items]
    head = LEAGUE_TITLE[league] + (' · ' + html.escape(date_title) if date_title else '')
    return head + '\n\n' + '\n'.join(lines)


def send_photo(token, chat, path, text):
    import requests
    with open(path, 'rb') as f:
        r = requests.post('https://api.telegram.org/bot%s/sendPhoto' % token, timeout=60,
                          data={'chat_id': chat, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': f})
    j = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    if not j.get('ok'):
        raise SystemExit('Telegram: %s' % (j.get('description') or r.status_code))


def main():
    league, items, date_title, chat = clean(load_payload())
    if league == 'NHL':
        import nhl
        nhl.register()
    import results_ice2 as ri
    out = os.path.join(os.getcwd(), 'itogi_%s.jpg' % league.lower())
    ri.render(items, out, variant=10, league=league, date_title=date_title or None)
    print('нарисовано:', out, '— матчей', len(items))
    token = os.environ.get('TG_BOT_TOKEN')
    if not token:
        print('TG_BOT_TOKEN не задан — картинка только сохранена')
        return
    if not chat:
        raise SystemExit('не указан чат (chat) для отправки')
    send_photo(token, chat, out, caption(league, items, date_title))
    print('отправлено в Telegram')


if __name__ == '__main__':
    main()
