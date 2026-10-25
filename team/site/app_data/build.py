# -*- coding: utf-8 -*-
"""Данные о командах для мини-приложения (team/site/app, владелец 25.10: «информация о командах и игроках — актуальная»).
Источники — те же, что у прогнозов: КХЛ — khl.api.webcaster.pro (team/picks/khl_data.py), НХЛ — api-web.nhle.com и
api.nhle.com/stats (разведка — team/site/app_data/probe.py). Ничего не публикует: пишет <out>/teams.json, сайт кладёт его в
приложение (team/site/build.py → <сайт>/app/data.json).

    python team/site/app_data/build.py 2026-10-25 out/app_data

Шестиугольник силы (0–100 — место среди команд своей лиги, 100 — лучшая): атака — голы за игру; защита — пропущенные за игру
(меньше — лучше); вратари — % отражённых бросков команды; большинство — КХЛ: голы в большинстве за игру, НХЛ: реализация
большинства; меньшинство — КХЛ: пропущенные в меньшинстве за игру (меньше — лучше), НХЛ: % нейтрализации; форма — очки за
последние 10 игр. Нет показателя — None (приложение его не рисует, не выдумывает).
"""
import json
import os
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for p in (os.path.join(ROOT, 'team', 'picks'), os.path.join(ROOT, 'render')):
    sys.path.insert(0, p)

import requests  # noqa: E402

import teams  # noqa: E402

AXES = ['Атака', 'Защита', 'Вратари', 'Большинство', 'Меньшинство', 'Форма']
LOWER_BETTER = {1, 4}           # защита (КХЛ и НХЛ — пропущенные), меньшинство в КХЛ — пропущенные в меньшинстве


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def scale(vals, lower=False):
    """Место среди команд лиги → 10…100 (лучшая — 100). None остаётся None."""
    xs = sorted(v for v in vals if v is not None)
    out = []
    for v in vals:
        if v is None or len(xs) < 2:
            out.append(None)
            continue
        worse = sum(1 for x in xs if (x > v if lower else x < v)) + 0.5 * (sum(1 for x in xs if x == v) - 1)
        out.append(round(10 + 90 * worse / (len(xs) - 1)))
    return out


def plain(s):
    """«Montréal Canadiens» → «montreal canadiens»: названия в двух API НХЛ пишутся по-разному."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '')) if not unicodedata.combining(c)).lower().strip()


def short_conf(c):
    """«Конференция «Восток»» → «Восток»."""
    c = str(c or '')
    for w in ('Восток', 'Запад'):
        if w in c:
            return w
    return c or None


def colors(name):
    """Цвета клуба как у баннеров канала (render/poster.py): основной, второй, акцент; слаг эмблемы."""
    try:
        import nhl
        import poster
        nhl.register()
        t = poster.TEAMS.get({'Рейнджерс': 'Нью-Йорк Рейнджерс', 'Айлендерс': 'Нью-Йорк Айлендерс'}.get(name, name))   # так их зовёт nhl_data
        if not t:
            return None, None
        hx = lambda c: '#%02x%02x%02x' % tuple(c)  # noqa: E731
        return t[0], [hx(t[1]), hx(t[2]), hx(poster.BANNER.get(name, poster.BANNER.get(t[0], t[1])))]
    except Exception as e:  # noqa: BLE001
        print('APPERR цвета %s: %r' % (name, e), flush=True)
        return None, None


def form_from_games(games, name):
    """КХЛ: последние 5 результатов (В/П) и очки за последние 10 игр (победа — 2, поражение в ОТ/буллитах — 1)."""
    gs = sorted((g for g in games if name in (g['h'], g['a'])), key=lambda g: g['d'])
    res, pts = [], []
    for g in gs:
        mine, other = (g['hg'], g['ag']) if g['h'] == name else (g['ag'], g['hg'])
        win = mine > other
        res.append('В' if win else 'П')
        pts.append(2 if win else 1 if g.get('e') else 0)
    return ''.join(res[-5:]), (sum(pts[-10:]) if pts else None), len(gs)


# ───────────────────────────── КХЛ

def khl(day):
    import khl_data
    games, _ = khl_data.fetch(day)
    boot = khl_data.get('data.json')
    stage = boot.get('current_stage_id')
    tbl = {(x.get('team') or x).get('id'): (x.get('team') or x) for x in khl_data.get('teams.json')}
    conf = {(x.get('team') or x).get('id'): (x.get('team') or x).get('conference') for x in khl_data.get('teams_v2.json?stage_id=%s' % stage)}
    rows = []
    for tid, name in teams.KHL_IDS.items():
        t = tbl.get(tid)
        if not t:
            continue
        gp = num(t.get('gp')) or 0
        my = [g for g in games if name in (g['h'], g['a'])]
        ppf = ppa = 0
        pp_known = 0
        for g in my:
            if g.get('ppg') is None:
                continue
            pp_known += 1
            h = g['h'] == name
            ppf += g['ppg'][0 if h else 1]
            ppa += g['ppg'][1 if h else 0]
        f5, l10, _ = form_from_games(games, name)
        players, goalies, sv, ga = khl_players(stage, tid)
        rows.append(dict(name=name, conf=short_conf(conf.get(tid) or t.get('conference')), gp=int(gp), pts=int(num(t.get('pts')) or 0),
                         w=int((num(t.get('w')) or 0) + (num(t.get('otw')) or 0) + (num(t.get('sow')) or 0)),
                         l=int((num(t.get('l')) or 0) + (num(t.get('otl')) or 0) + (num(t.get('sol')) or 0)),
                         gf=int(num(t.get('gf')) or 0), ga=int(num(t.get('ga')) or 0), form=f5, l10=l10,
                         coach=(t.get('head_coach') or {}).get('name'), players=players, goalies=goalies,
                         raw=[(num(t.get('gf')) or 0) / gp if gp else None, (num(t.get('ga')) or 0) / gp if gp else None,
                              sv / (sv + ga) if sv + ga else None, ppf / pp_known if pp_known else None,
                              ppa / pp_known if pp_known else None, l10]))
    return finish(rows, lower={1, 4})


def khl_players(stage, tid):
    """Игроки команды со статистикой сезона (players_v2: по 16 на странице). → (полевые топ-8 по очкам, вратари, отражено, пропущено)."""
    import khl_data
    allp = []
    for page in range(1, 8):
        try:
            arr = khl_data.get('players_v2.json?stage_id=%s&q[team_id_eq]=%s&page=%d' % (stage, tid, page))
        except Exception as e:  # noqa: BLE001
            print('APPERR игроки КХЛ %s стр.%d: %r' % (tid, page, e), flush=True)
            break
        if not isinstance(arr, list) or not arr:
            break
        allp += [x.get('player') or x for x in arr]
        if len(arr) < 16:
            break
        time.sleep(0.2)
    sk, gk, sv, ga = [], [], 0, 0
    for p in allp:
        if ((p.get('team') or {}).get('id')) not in (tid, None):
            continue
        st = {s.get('id'): s.get('val') for s in p.get('stats') or []}
        role = str(p.get('role_key') or '')
        if not st.get('gp'):
            continue
        if 'goal' in role:
            sv += st.get('sv') or 0
            ga += st.get('ga') or 0
            gk.append(dict(n=p.get('name'), no=p.get('shirt_number'), gp=st.get('gp'), w=st.get('w'), sv=st.get('sv_pct'), gaa=st.get('gaa'), so=st.get('so')))
        else:
            sk.append(dict(n=p.get('name'), no=p.get('shirt_number'), pos='защ.' if 'def' in role else 'нап.', gp=st.get('gp'),
                           g=st.get('g'), a=st.get('a'), pts=st.get('pts'), pm=st.get('pm')))
    sk.sort(key=lambda x: (-(x['pts'] or 0), -(x['g'] or 0)))
    gk.sort(key=lambda x: -(x['gp'] or 0))
    return sk[:8], gk[:3], sv, ga


# ───────────────────────────── НХЛ

def nhl(day):
    web = 'https://api-web.nhle.com/v1/'
    S = requests.Session()
    S.headers['User-Agent'] = 'Mozilla/5.0'
    get = lambda u: S.get(u, timeout=30).json()  # noqa: E731
    y = int(day[:4]) if int(day[5:7]) >= 9 else int(day[:4]) - 1
    st = get(web + 'standings/now').get('standings') or []
    summ = {plain(x.get('teamFullName')): x for x in get('https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId=%d%d%%20and%%20gameTypeId=2' % (y, y + 1)).get('data') or []}
    rows = []
    for s in st:
        ab = (s.get('teamAbbrev') or {}).get('default')
        if ab not in teams.NHL:
            continue
        name, full = teams.NHL[ab][0], teams.NHL[ab][1]
        m = summ.get(plain(full)) or {}
        gp = s.get('gamesPlayed') or 0
        sapg = num(m.get('shotsAgainstPerGame'))
        shots = sapg * gp if sapg and gp else None
        players, goalies = [], []
        try:
            cs = get(web + 'club-stats/%s/now' % ab)
            nm = lambda x: ('%s %s' % ((x.get('firstName') or {}).get('default', ''), (x.get('lastName') or {}).get('default', ''))).strip()  # noqa: E731
            for x in sorted(cs.get('skaters') or [], key=lambda x: (-(x.get('points') or 0), -(x.get('goals') or 0)))[:8]:
                players.append(dict(n=nm(x), pos='защ.' if x.get('positionCode') == 'D' else 'нап.', gp=x.get('gamesPlayed'),
                                    g=x.get('goals'), a=x.get('assists'), pts=x.get('points'), pm=x.get('plusMinus')))
            for x in sorted(cs.get('goalies') or [], key=lambda x: -(x.get('gamesPlayed') or 0))[:3]:
                goalies.append(dict(n=nm(x), gp=x.get('gamesPlayed'), w=x.get('wins'), sv=round(100 * (x.get('savePercentage') or 0), 1),
                                    gaa=round(x.get('goalsAgainstAverage') or 0, 2), so=x.get('shutouts')))
        except Exception as e:  # noqa: BLE001
            print('APPERR игроки НХЛ %s: %r' % (ab, e), flush=True)
        ga = s.get('goalAgainst') or 0
        rows.append(dict(name=name, conf={'E': 'Восток', 'W': 'Запад'}.get(s.get('conferenceAbbrev'), s.get('conferenceName')),
                         place=s.get('conferenceSequence'), gp=gp, pts=s.get('points'), w=s.get('wins'),
                         l=(s.get('losses') or 0) + (s.get('otLosses') or 0), gf=s.get('goalFor'), ga=ga, form=None,
                         l10=s.get('l10Points'), l10s='%s–%s–%s' % (s.get('l10Wins'), s.get('l10Losses'), s.get('l10OtLosses')),
                         players=players, goalies=goalies,
                         raw=[(s.get('goalFor') or 0) / gp if gp else None, ga / gp if gp else None,
                              (shots - ga) / shots if shots else None, num(m.get('powerPlayPct')), num(m.get('penaltyKillPct')), s.get('l10Points')]))
    return finish(rows, lower={1})


def finish(rows, lower):
    """Шкала 10–100 по каждому показателю внутри лиги, место в конференции (если источник не дал), цвета и эмблема."""
    for k in range(len(AXES)):
        for r, v in zip(rows, scale([r['raw'][k] for r in rows], lower=k in lower)):
            r.setdefault('axes', []).append(v)
    for c in {r['conf'] for r in rows}:
        grp = sorted((r for r in rows if r['conf'] == c), key=lambda r: (-(r['pts'] or 0), r['gp'], -((r['gf'] or 0) - (r['ga'] or 0))))
        for i, r in enumerate(grp, 1):
            r.setdefault('place', i)
    for r in rows:
        r['slug'], r['colors'] = colors(r['name'])
        r['raw'] = [round(v, 3) if isinstance(v, float) else v for v in r['raw']]
    return rows


def main():
    day, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    res = dict(updated=date.today().isoformat(), axes=AXES, leagues={})
    for lg, fn in (('khl', khl), ('nhl', nhl)):
        try:
            res['leagues'][lg] = fn(day)
            print('APP %s: команд %d' % (lg, len(res['leagues'][lg])), flush=True)
        except Exception as e:  # noqa: BLE001 — одна лига не собралась — вторая всё равно уходит
            print('APPERR %s: %r' % (lg, e), flush=True)
    with open(os.path.join(out, 'teams.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
