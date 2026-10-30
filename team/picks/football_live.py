# -*- coding: utf-8 -*-
"""Футбол: вероятности модели и линия Pinnacle на матчи дня (ТЗ docs/handoff/FOOTBALL_BRIEF.md, п. 4; этап 2 — в бот).

  • сила клубов — football_model.py по истории football_hist.py (лиги — football-data, xG — Understat / по ударам);
    константы — лучшие по проверке на истории (football_bt.py, calib.json → FOOT);
  • еврокубки — сила в лиге × сила лиги (football_bt.fit_league_factors по еврокубкам прошлых лет);
  • линия — Pinnacle guest API (как хоккей, pin.py), без ключа; кэфы moneyline/total — матч (period 0 = 90 минут).
Печатает FOOT (матч, λ, вероятности, кэфы) и FOOTPICK (самая вероятная ставка с кэфом ≥ 1,6 и p ≥ FOOT_P, «ВЫБОР»).
Боевых прогнозов не шлёт. Отдельно: python team/picks/football_live.py E0 2026-10-31"""
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import football_hist as FH  # noqa: E402
import football_model as FM  # noqa: E402

API = 'https://guest.api.arcadia.pinnacle.com/0.1'
PIN = {'E0': 1980, 'SP1': 2196, 'I1': 2436, 'D1': 1842, 'F1': 2036, 'P1': 2386, 'UCL': 2627, 'UEL': 2630, 'UECL': 214101}
HDR = dict(FH.UA, Accept='application/json')
MSK = timezone(timedelta(hours=3))
CALIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calib.json')


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def conf():
    c = json.load(open(CALIB, encoding='utf-8')).get('FOOT') or {}
    P = dict(FM.P0, **(c.get('P') or {}))
    return P, c


def dec(a):
    a = float(a)
    return round(1 + a / 100, 3) if a > 0 else round(1 + 100 / abs(a), 3)


def pin_day(lg, day):
    """Матчи дня (по Москве) и кэфы 90 минут: {(хозяева, гости): {вид: кэф}}."""
    mu = requests.get('%s/leagues/%d/matchups' % (API, PIN[lg]), headers=HDR, timeout=30).json()
    mk = requests.get('%s/leagues/%d/markets/straight' % (API, PIN[lg]), headers=HDR, timeout=30).json()
    pairs = {}
    for m in mu:
        if m.get('parentId') or m.get('units') not in (None, 'Regular') or not m.get('startTime'):
            continue
        st = datetime.fromisoformat(m['startTime'].replace('Z', '+00:00')).astimezone(MSK)
        if st.strftime('%Y-%m-%d') != day:
            continue
        side = {p.get('alignment'): p.get('name') for p in m.get('participants') or []}
        if side.get('home') and side.get('away'):
            pairs[m['id']] = (side['home'], side['away'], st.strftime('%H:%M'))
    odds = {k: {} for k in pairs}
    for x in mk:
        mid = x.get('matchupId')
        if mid not in pairs or x.get('period') != 0:
            continue
        pr = {p.get('designation'): (p.get('points'), dec(p['price'])) for p in x.get('prices') or [] if p.get('price') is not None}
        if x.get('type') == 'moneyline' and len(pr) == 3:
            odds[mid].update({'П1': pr['home'][1], 'Х': pr['draw'][1], 'П2': pr['away'][1]})
        elif x.get('type') == 'spread' and 'home' in pr and 'away' in pr:
            # фора +0,5 = «не проиграет» (1Х / Х2), у Pinnacle она среди альтернативных фор
            if pr['home'][0] == 0.5:
                odds[mid]['1Х'] = pr['home'][1]
            if pr['away'][0] == 0.5:
                odds[mid]['Х2'] = pr['away'][1]
        elif x.get('type') == 'total' and 'over' in pr:
            ln = pr['over'][0]
            if ln in (1.5, 2.5, 3.5):
                odds[mid]['ТБ %.1f' % ln] = pr['over'][1]
                odds[mid]['ТМ %.1f' % ln] = pr['under'][1]
    return {pairs[k]: odds[k] for k in pairs}


def main(lg, day):
    P, C = conf()
    floor = C.get('FOOT_P', 0.6)
    data = FH.load()
    cal = C.get('calib') or {}
    if lg in FH.OURS:
        games = sorted(data['dom'][lg], key=lambda g: g['d'])
        coef = C.get('xg_coef', {}).get(lg, (0.3, 0.03))
        for g in games:
            if C.get('xg') == 'us' and g.get('xg'):
                g['x'] = g['xg']
            elif 'st' in g and C.get('xg') in ('us', 'shots'):
                g['x'] = [coef[0] * g['st'][i] + coef[1] * max(0, g['sh'][i] - g['st'][i]) for i in (0, 1)]
        cur = FH.season_of(day)
        known = {g['h'] for g in games if g['s'] == cur - 1}
        R, mh, ma = FM.fit(games, day, P, known)
        names = sorted({g['h'] for g in games if g['s'] == cur})
    else:
        out('FOOTERR', 'еврокубки в football_live — после проверки (этап 2)')
        return
    try:
        line = pin_day(lg, day)
    except Exception as e:
        out('FOOTERR', 'Pinnacle: %r' % e)
        line = {}
    for (ph, pa, t), od in line.items():
        h, a = FH.match_name(ph, names), FH.match_name(pa, names)
        if not h or not a:
            out('FOOTERR', 'нет в истории: %s — %s' % (ph, pa))
            continue
        lh, la = FM.lambdas(R, mh, ma, h, a, P)
        m = FM.markets(lh, la, P['rho'])
        pr = {}
        for k, p in m.items():
            ab = cal.get(k)
            if ab:
                x = math.log(max(1e-6, p) / max(1e-6, 1 - p))
                p = 1 / (1 + math.exp(-(ab[0] + ab[1] * x)))
            pr[k] = p
        out('FOOT', '%s %s | %s — %s | λ %.2f : %.2f | %s' % (day, t, h, a, lh, la, ' · '.join(
            '%s %.0f%%%s' % (k, 100 * pr[k], ' @%.2f' % od[k] if k in od else '') for k in sorted(pr) if k in od or k in ('1Х', 'Х2', 'ОЗ да', 'ОЗ нет'))))
        ok = [(pr[k], k, od[k]) for k in od if k in pr and od[k] >= 1.6 and pr[k] >= floor]
        if ok:
            p, k, o = max(ok)
            out('FOOTPICK', '%s — %s | ВЫБОР %s @%.2f | p %.0f%%' % (h, a, k, o, 100 * p))
        else:
            out('FOOTPICK', '%s — %s | нет ставки от %.0f%% с кэфом от 1,6' % (h, a, 100 * floor))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else datetime.now(MSK).strftime('%Y-%m-%d'))
