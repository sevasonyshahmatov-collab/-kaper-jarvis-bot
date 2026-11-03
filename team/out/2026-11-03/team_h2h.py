# -*- coding: utf-8 -*-
"""Сборщик личных встреч для страниц команд макета v3a: матчи регулярки двух прошлых сезонов (2024/25 и 2025/26)
каждого клуба КХЛ и НХЛ. Запуск из корня репозитория, в задании: "make": ["team/out/2026-11-03/team_h2h.py"].
Результат — в лог (H2HJSON, gzip+base64): артефакт из облака не скачать."""
import base64, gzip, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import requests  # noqa: E402
import teams  # noqa: E402
import khl_data  # noqa: E402

MSK = timezone(timedelta(hours=3))
res = {'khl': {}, 'nhl': {}, 'err': []}
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0'
YEARS = (2024, 2025)
lab = lambda y: '%d/%02d' % (y, (y + 1) % 100)


def web(path):
    for k in range(3):
        try:
            r = S.get('https://api-web.nhle.com/v1/' + path, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            if k == 2:
                res['err'].append('NHL %s: %r' % (path, e)); print('H2HERR', path, repr(e), flush=True)
                return None
            time.sleep(1 + k)


def nhl(ab):
    name = teams.NHL_RU[ab]
    rows = []
    for y in YEARS:
        sch = web('club-schedule-season/%s/%d%d' % (ab, y, y + 1)) or {}
        for g in sch.get('games') or []:
            if g.get('gameType') != 2 or g.get('gameState') not in ('OFF', 'FINAL'):
                continue
            h, a = g['homeTeam'], g['awayTeam']
            if h.get('score') is None:
                continue
            home = h.get('abbrev') == ab
            op = a if home else h
            lp = (g.get('gameOutcome') or {}).get('lastPeriodType')
            d = datetime.fromisoformat(g['startTimeUTC'].replace('Z', '+00:00')).astimezone(MSK).strftime('%Y-%m-%d')
            rows.append({'s': lab(y), 'd': d, 'o': teams.NHL_RU.get(op.get('abbrev'), op.get('abbrev')), 'h': 1 if home else 0,
                         'gf': h['score'] if home else a['score'], 'ga': a['score'] if home else h['score'],
                         'x': 'ОТ' if lp == 'OT' else 'Б' if lp == 'SO' else ''})
    print('H2H НХЛ %s: %d' % (name, len(rows)), flush=True)
    return name, rows


with ThreadPoolExecutor(4) as ex:
    for name, rows in ex.map(nhl, list(teams.NHL_RU)):
        res['nhl'][name] = rows

try:
    boot = khl_data.get('data.json')
    stages = boot.get('stages_v2') or []
    print('H2HSTAGES', json.dumps([{k: s.get(k) for k in ('id', 'season', 'title', 'name', 'type', 'stage_type', 'type_id')} for s in stages],
                                  ensure_ascii=False, separators=(',', ':'))[:6000], flush=True)
    def start_year(s):
        m = re.search(r'(20\d\d)', str(s.get('season') or ''))
        return int(m.group(1)) if m else None
    cand = [s for s in stages if start_year(s) in YEARS]
    txt = lambda s: ('%s %s %s' % (s.get('title'), s.get('name'), s.get('stage_type') or s.get('type'))).lower()
    reg = [s for s in cand if 'регуляр' in txt(s) or 'regular' in txt(s)]
    if not reg:
        reg = [s for s in cand if not re.search(r'плей|play|кубок|cup|звезд|star|предсез|товар|friend', txt(s))]
    print('H2HPICK', [(s.get('id'), s.get('season'), s.get('title') or s.get('name')) for s in reg], flush=True)
    for s in reg:
        y = start_year(s)
        events = []
        for page in range(1, 121):
            arr = khl_data.get('events_v2.json?order_direction=asc&page=%d&stage_id=%s' % (page, s['id']))
            if not isinstance(arr, list) or not arr:
                break
            for w in arr:
                e = w.get('event') or w
                if e and e.get('type_id') in (18, 24) and e.get('game_state_key') == 'finished':
                    events.append(e)
            if len(arr) < 16:
                break
        need = [e for e in events if 'scores' not in e]
        with ThreadPoolExecutor(8) as ex:
            det = dict(zip([e['id'] for e in need], ex.map(khl_data.detail, need)))
        n = 0
        for e in events:
            src = det.get(e['id']) or e
            sc = str(src.get('score') or e.get('score') or '').split(':')
            if len(sc) != 2:
                continue
            sx = src.get('scores') or {}
            x = 'Б' if sx.get('bullitt') else 'ОТ' if sx.get('overtime') else ''
            h, a = khl_data.team(src.get('team_a') or e.get('team_a')), khl_data.team(src.get('team_b') or e.get('team_b'))
            d = khl_data.msk(src.get('start_at') or e.get('start_at'))[:10]
            hg, ag = int(sc[0]), int(sc[1])
            for me, op, home, gf, ga in ((h, a, 1, hg, ag), (a, h, 0, ag, hg)):
                res['khl'].setdefault(me, []).append({'s': lab(y), 'd': d, 'o': op, 'h': home, 'gf': gf, 'ga': ga, 'x': x})
            n += 1
        print('H2H КХЛ %s: матчей %d' % (lab(y), n), flush=True)
except Exception as e:  # noqa: BLE001
    res['err'].append('KHL: %r' % e); print('H2HERR KHL', repr(e), flush=True)

raw = json.dumps(res, ensure_ascii=False, separators=(',', ':'))
b = base64.b64encode(gzip.compress(raw.encode('utf-8'), 9)).decode()
CH = 3000
for i in range(0, len(b), CH):
    print('H2HJSON %d %d %s' % (i // CH, (len(b) + CH - 1) // CH, b[i:i + CH]), flush=True)
print('H2HDONE', len(raw), 'байт; ошибок', len(res['err']), flush=True)
