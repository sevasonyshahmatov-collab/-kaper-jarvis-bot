# -*- coding: utf-8 -*-
"""Игроки КХЛ для раздела «Игроки» (макет v3a, владелец 03.11). Источник — приложение КХЛ (khl.api.webcaster.pro):
players_v2 — фото, позиция, номер, статистика сезона (игры, голы, передачи, TOI); event_v2 — авторы голов и передач
в каждом сыгранном матче. Бросков по игрокам приложение не отдаёт. Результат — hockey/data/khl_players.json в формате
nhl_players.json (log: [дата, команда, соперник, дома, голы, передачи, None, None, 0]; gp — игры игрока за сезон)."""
import json, os, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

B = 'https://khl.api.webcaster.pro/api/khl_mobile/'
MSK = timezone(timedelta(hours=3))
H = os.path.dirname(os.path.abspath(__file__))
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
SLUG = {8: 'dinamo_msk', 10: 'avangard', 12: 'amur', 16: 'cska', 18: 'spartak', 22: 'torpedo', 24: 'sibir', 26: 'lokomotiv',
        28: 'traktor', 30: 'metallurg', 32: 'salavat', 36: 'neftekhimik', 38: 'dinamo_minsk', 40: 'akbars', 42: 'severstal',
        44: 'ska', 46: 'barys', 56: 'avtomobilist', 61: 'admiral', 105: 'lada', 113: 'sochi', 315: 'shanghai'}
err = []


def get(p):
    for k in range(4):
        try:
            r = S.get(B + p, timeout=45)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception as e:  # noqa: BLE001
            if k == 3:
                err.append('%s %r' % (p[:80], e))
        time.sleep(1 + k)
    return None


def msk(ts):
    v = float(ts or 0)
    return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, MSK).strftime('%Y-%m-%d %H:%M')


boot = get('data.json') or {}
stage = boot.get('current_stage_id')

# ── игроки по клубам
def club(tid):
    allp = []
    for page in range(1, 10):
        arr = get('players_v2.json?stage_id=%s&q[team_id_eq]=%s&page=%d' % (stage, tid, page))
        if not isinstance(arr, list) or not arr:
            break
        allp += [x.get('player') or x for x in arr]
        if len(arr) < 16:
            break
    # имена латиницей (владелец 09.11: «все имена английскими») — то же приложение с locale=en; сайт переводит их в daily/split.py
    for page in range(1, 10):
        arr = get('players_v2.json?stage_id=%s&q[team_id_eq]=%s&page=%d&locale=en' % (stage, tid, page))
        if not isinstance(arr, list) or not arr:
            break
        for x in arr:
            q = x.get('player') or x
            if q.get('id') is not None and q.get('name'):
                EN_ID[q['id']] = q['name']
        if len(arr) < 16:
            break
    return tid, allp


EN_ID = {}
P, by_num, GIMG = {}, {}, {}
CLUBS = []
with ThreadPoolExecutor(6) as ex:
    for tid, allp in ex.map(club, list(SLUG)):
        CLUBS.append((tid, allp))
        for p in allp:
            if ((p.get('team') or {}).get('id')) not in (tid, None):
                continue
            stt = {s.get('id'): s.get('val') for s in p.get('stats') or []}
            role = str(p.get('role_key') or '')
            if 'goal' in role and p.get('image'):
                GIMG.setdefault(SLUG[tid], {})[p.get('name') or ''] = p['image']   # фото вратарей для «Лучший вратарь»
            if 'goal' in role or not stt.get('gp'):
                continue
            r = {'id': p['id'], 'n': p.get('name') or '', 't': SLUG[tid], 'img': p.get('image'), 'no': p.get('shirt_number'),
                 'pos': 'D' if 'def' in role else 'F', 'gp': stt.get('gp'), 'toi_avg': stt.get('toi_avg'),
                 'st': {k: v for k, v in stt.items() if v is not None}, 'log': []}  # st — все показатели приложения (для навыков)
            P[p['id']] = r
            by_num[(tid, p.get('shirt_number'))] = r
print('KHLP players', len(P), flush=True)
print('KHLP stat ids', sorted({k for r in P.values() for k in r['st']}), flush=True)  # какие показатели отдаёт приложение

# ── матчи этапа
events = []
frm = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()); to = int(time.time()) + 10 * 86400
for page in range(1, 81):
    arr = get('events_v2.json?order_direction=asc&page=%d&q%%5Bstart_at_gt_time_from_unixtime%%5D=%d'
              '&q%%5Bstart_at_lt_time_from_unixtime%%5D=%d&stage_id=%s' % (page, frm, to, stage))
    if not isinstance(arr, list) or not arr:
        break
    events += [e for e in ((w.get('event') or w) for w in arr) if e and e.get('type_id') in (18, 24)]
    if len(arr) < 16:
        break
done = [e for e in events if e.get('game_state_key') == 'finished']
nxt = {}
for e in sorted((e for e in events if e.get('game_state_key') != 'finished'), key=lambda e: float(e.get('start_at') or 0)):
    a, b = (e.get('team_a') or {}).get('id'), (e.get('team_b') or {}).get('id')
    for me, op, home in ((a, b, 1), (b, a, 0)):
        if me in SLUG and op in SLUG and SLUG[me] not in nxt:
            nxt[SLUG[me]] = {'d': msk(e.get('start_at')), 'o': SLUG[op], 'h': home}


def det(e):
    d = get('event_v2.json?id=%s' % e['id'])
    return e, (d.get('event') or d) if d else None


# статистика сыгранных матчей — с 11.11 (владелец: «старые можно не заполнять»); поля приложения: shots — броски в створ, ppg/ppc — голы
# в большинстве / число большинств, shg — голы в меньшинстве, vbr — выигранные вбрасывания, pim — штрафные минуты
MS_FROM = '2026-11-10'    # 10.11 — для проверки на уже сыгранных матчах
MS_KEYS = ('shots', 'ppg', 'ppc', 'shg', 'vbr', 'pim', 'total_puck_control_time', 'total_distance_travelled', 'offensive_blue_line_crossings_count')
MST = {}
team_games = {}
with ThreadPoolExecutor(8) as ex:
    for e, d in ex.map(det, done):
        if not d:
            continue
        a, b = (d.get('team_a') or {}).get('id'), (d.get('team_b') or {}).get('id')
        if a not in SLUG or b not in SLUG:
            continue
        day = msk(d.get('start_at') or e.get('start_at'))
        if day[:10] >= MS_FROM:                          # статистика матча для страницы сыгранного матча (владелец 11.11)
            try:
                ta, tb = d.get('team_a') or {}, d.get('team_b') or {}
                pn = [0, 0]
                for v in d.get('violations') or []:
                    vt = (v.get('violator') or {}).get('team_id')
                    if vt in (a, b):
                        pn[vt == b] += 1
                MST['khl|%s|%s|%s' % (day[:10], SLUG[a], SLUG[b])] = {
                    'h': {k: ta.get(k) for k in MS_KEYS if ta.get(k) is not None}, 'a': {k: tb.get(k) for k in MS_KEYS if tb.get(k) is not None},
                    'pn': pn if sum(pn) else None,
                    # удаления по минутам (владелец 11.11): [период, время, минут штрафа, причина, игрок, номер, сторона h/a]
                    'pl': [[v.get('period'), v.get('time'), v.get('penalty_time'), v.get('penalty_reason'),
                            (v.get('violator') or {}).get('name'), (v.get('violator') or {}).get('shirt_number'),
                            'h' if (v.get('violator') or {}).get('team_id') == a else 'a' if (v.get('violator') or {}).get('team_id') == b else None]
                           for v in d.get('violations') or []],
                    'vk': sorted((d.get('violations') or [{}])[0].get('violator') or {})[:20]}   # поля игрока — для сверки формата
            except Exception as x:  # noqa: BLE001
                err.append('mstats %s %r' % (e.get('id'), x))
        pts = {}
        for g in d.get('goals') or []:
            au = g.get('author') or {}
            tid = au.get('team_id')
            if tid not in (a, b):
                continue
            k = (tid, au.get('shirt_number')); pts.setdefault(k, [0, 0])[0] += 1
            for x in g.get('assistants') or []:
                pts.setdefault((tid, x.get('shirt_number')), [0, 0])[1] += 1
        for me, op, home in ((a, b, 1), (b, a, 0)):
            team_games.setdefault(me, []).append((day, op, home, pts))

for tid, gs in team_games.items():
    gs.sort(key=lambda x: x[0])
    for (t2, num), r in by_num.items():
        if t2 != tid:
            continue
        for day, op, home, pts in gs:
            g, a = pts.get((tid, num), [0, 0])
            r['log'].append([day, SLUG[tid], SLUG[op], home, g, a, None, None, 0])

out = [r for r in P.values() if r['log']]
res = {'built': datetime.now(MSK).strftime('%Y-%m-%d %H:%M'), 'season': '2026/27', 'league': 'khl', 'next': nxt, 'players': out, 'gimg': GIMG,
       'err': err[:30], 'note': 'log — все матчи команды (кто играл в каком матче, приложение не отдаёт); gp — игры игрока'}
os.makedirs(os.path.join(H, 'data'), exist_ok=True)
# таблица имён ru → en для сайта: старые записи остаются (игрок ушёл из клуба — имя всё равно нужно в истории)
ENF = os.path.join(H, 'data', 'khl_names_en.json')
try:
    EN = json.load(open(ENF, encoding='utf-8'))
except Exception:  # noqa: BLE001
    EN = {}
for tid_, allp_ in CLUBS:
    for q in allp_:
        if q.get('name') and EN_ID.get(q.get('id')):
            EN[q['name']] = EN_ID[q['id']]
with open(ENF, 'w', encoding='utf-8') as f:
    json.dump(EN, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
with open(os.path.join(H, 'data', 'khl_players.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, separators=(',', ':'))
print('KHLP done players', len(out), 'games', len(done), 'errors', len(err), flush=True)
try:                                                     # hockey/data/khl_mstats.json: прежние матчи остаются, новые добавляются
    f_ms = os.path.join(H, 'data', 'khl_mstats.json')
    old = json.load(open(f_ms, encoding='utf-8')) if os.path.exists(f_ms) else {}
    old.update(MST)
    with open(f_ms, 'w', encoding='utf-8') as f:
        json.dump(old, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print('KHLP mstats', len(MST), 'всего', len(old), flush=True)
except Exception as x:  # noqa: BLE001
    print('KHLP mstats ошибка %r' % x, flush=True)

