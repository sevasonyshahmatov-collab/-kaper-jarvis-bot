# -*- coding: utf-8 -*-
"""Матчи регулярного чемпионата КХЛ этого сезона из официального приложения КХЛ (khl.api.webcaster.pro — тот же источник,
что у таблицы КХЛ, лист «КХЛ_матчи_приложение») — для расчёта «Что заходит» по паре (как конструктор матча в таблице)
и доводов к прогнозам на 15.10 (Лада — СКА, Северсталь — Локомотив).
Облачная сессия до API не достаёт, Actions — достаёт: скрипт печатает в лог строки «KHLG {json}» (сыгранные матчи),
«KHLNEXT {json}» (матчи дня с полем bets) и «KHLSTAGE {json}»; их читают из лога. Ничего не рисует и никуда не шлёт.
Запуск: python team/out/2026-10-15/khl_fetch.py [YYYY-MM-DD — день прогнозов по МСК, по умолчанию 2026-10-15]"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

DAY = sys.argv[1] if len(sys.argv) > 1 else '2026-10-15'
BASE = 'https://khl.api.webcaster.pro/api/khl_mobile/'
MSK = timezone(timedelta(hours=3))
IDS = {8: 'Динамо Москва', 10: 'Авангард', 12: 'Амур', 16: 'ЦСКА', 18: 'Спартак', 22: 'Торпедо', 24: 'Сибирь', 26: 'Локомотив',
       28: 'Трактор', 30: 'Металлург', 32: 'Салават Юлаев', 36: 'Нефтехимик', 38: 'Динамо Минск', 40: 'Ак Барс', 42: 'Северсталь',
       44: 'СКА', 46: 'Барыс', 56: 'Автомобилист', 61: 'Адмирал', 105: 'Лада', 113: 'Сочи', 315: 'Шанхайские Драконы'}
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'


def get(path):
    r = S.get(BASE + path, timeout=40)
    r.raise_for_status()
    return r.json()


def out(tag, obj):
    print(tag + ' ' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')), flush=True)


def team(t):
    t = t or {}
    return IDS.get(t.get('id')) or str(t.get('name') or '').strip()


def day_msk(ts):
    if isinstance(ts, str) and not ts.isdigit():
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(MSK).strftime('%Y-%m-%d %H:%M')
    v = float(ts or 0)
    return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, MSK).strftime('%Y-%m-%d %H:%M')


boot = get('data.json')
stage = boot.get('current_stage_id')
st = next((x for x in boot.get('stages_v2') or [] if x.get('id') == stage), {})
out('KHLSTAGE', {'stage': stage, 'season': st.get('season'), 'title': st.get('title') or st.get('name')})
year = int(str(st.get('season') or DAY)[:4])
frm = int(datetime(year, 8, 1, tzinfo=timezone.utc).timestamp())
to = int(datetime.fromisoformat(DAY).replace(tzinfo=MSK).timestamp()) + 2 * 86400

events = []
for page in range(1, 41):
    q = ('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
         '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, stage))
    arr = get(q)
    if not isinstance(arr, list) or not arr:
        break
    for w in arr:
        e = w.get('event') or w
        if e and e.get('type_id') in (18, 24):
            events.append(e)
    if len(arr) < 16:
        break
print('событий:', len(events), flush=True)

done = [e for e in events if e.get('game_state_key') == 'finished']


def detail(e):
    for k in range(3):
        try:
            j = get('event_v2.json?id=%s' % e['id'])
            return j.get('event') or j
        except Exception as err:  # noqa: BLE001
            if k == 2:
                print('KHLERR', e.get('id'), err, flush=True)
                return None
            time.sleep(1 + k)


with ThreadPoolExecutor(8) as ex:
    details = list(ex.map(detail, done))

for e, d in zip(done, details):
    src = d or e
    sc = str(src.get('score') or e.get('score') or '').split(':')
    if len(sc) != 2:
        continue
    s = src.get('scores') or {}
    end = 'Б' if s.get('bullitt') else 'ОТ' if s.get('overtime') else ''
    out('KHLG', {'d': day_msk(src.get('start_at') or e.get('start_at')), 'id': e.get('id'), 'h': team(src.get('team_a') or e.get('team_a')),
                 'a': team(src.get('team_b') or e.get('team_b')), 'hg': int(sc[0]), 'ag': int(sc[1]), 'e': end, 's': s})

for e in events:
    if e.get('game_state_key') == 'finished':
        continue
    start = e.get('start_at') or 0
    if not day_msk(start).startswith(DAY):
        continue
    d = detail(e) or e
    out('KHLNEXT', {'d': day_msk(start), 'id': e.get('id'), 'h': team(e.get('team_a')), 'a': team(e.get('team_b')),
                    'bets': d.get('bets') or e.get('bets'), 'keys': sorted(list(d.keys()))[:60]})
