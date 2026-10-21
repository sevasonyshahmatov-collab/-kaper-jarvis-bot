"""Сколько было бы в банке, если ставить на каждый прогноз таблицы с начала сезона (владелец 21.10: «если бы я начал
ставить по таблице на все события, 20 % от банка начиная с 2000, сколько бы у меня сейчас было? Коэффициенты не из
таблицы»). Два расчёта — КХЛ и НХЛ. Прогноз таблицы — как в трейлере (render/sheet_data.rolling): модель «накануне»
матча, ставка на итоговую победу (с ОТ и буллитами) фаворита модели.

Кэфы:
- НХЛ — настоящие закрывающие кэфы на победу с ОТ из архива табло ESPN (линия DraftKings) за каждый игровой день;
  матча нет в архиве — расчётный кэф, как у КХЛ (сколько таких — в логе).
- КХЛ — архива линий нет: кэф расчётный, как у букмекеров — вероятность по рейтингу силы Elo ДО матча (независимо от
  модели таблицы) плюс маржа 6 %.
Банк: 2000, ставка — 10 % от текущего банка (владелец 21.10; для сравнения 20 % и 5 %), плюс ровная ставка 100. В лог — итоги, худшая
просадка, серия банка; владельцу — сводка текстом. Никуда не выкладывается."""
import json
import os
import sys
from datetime import datetime, timedelta

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for p in ('team/picks', 'render'):
    sys.path.insert(0, os.path.join(ROOT, p))
import calc  # noqa: E402
import espn  # noqa: E402
import sheet_data  # noqa: E402

DAY = '2026-10-21'
MARGIN = 1.06
START = 2000.0


def elo_pre(G, k=20.0, home=40.0):
    """Вероятность победы хозяев (с ОТ) по Elo ДО каждого матча — как рынок видел бы силы команд."""
    R, out = {}, []
    for g in G:
        h, a = g['home'], g['away']
        rh, ra = R.get(h, 1500.0), R.get(a, 1500.0)
        e = 1 / (1 + 10 ** ((ra - rh - home) / 400))
        out.append(e)
        s = 1.0 if g['hg'] > g['ag'] else 0.0
        if g['ot']:
            s = 0.6 if s else 0.4
        R[h], R[a] = rh + k * (s - e), ra - k * (s - e)
    return out


def calc_odds(p):
    return round(min(8.0, max(1.12, 1 / (p * MARGIN))), 2)


def espn_lines(G):
    """{(хозяева, гости, день США): (кэф хозяев, кэф гостей)} — закрывающая линия на победу с ОТ."""
    import nhl_data
    days = sorted({(datetime.fromisoformat(g['d']) - timedelta(hours=8)).date().isoformat() for g in G})
    out = {}
    for d in days:
        try:
            j = requests.get(espn.URL, params={'dates': d.replace('-', '')}, headers=espn.HDR, timeout=30).json()
        except (requests.RequestException, ValueError) as e:
            print('BANKERR ESPN %s: %r' % (d, e), flush=True)
            continue
        for ev in j.get('events') or []:
            c = (ev.get('competitions') or [{}])[0]
            side = {t.get('homeAway'): espn.AB.get(espn._get(t, 'team', 'abbreviation'), espn._get(t, 'team', 'abbreviation'))
                    for t in c.get('competitors') or []}
            odds = (c.get('odds') or [None])[0]
            if not odds:
                continue
            ml = next((m for m in espn.markets(odds) if m['type'] == 'moneyline'), None)
            if ml:
                out[(nhl_data.ru(side.get('home')), nhl_data.ru(side.get('away')), d)] = (ml['prices'][0]['price'],
                                                                                          ml['prices'][1]['price'])
    print('BANK ESPN: дней %d, матчей с линией %d' % (len(days), len(out)), flush=True)
    return out


def run(league, raw):
    G = calc.prep(raw)
    roll = sheet_data.rolling(G)
    pe = elo_pre(G)
    lines = espn_lines(raw) if league == 'NHL' else {}
    by_id = {(r['h'], r['a'], r['d'][:10]): r for r in raw}
    bets, real = [], 0
    for (g, p), e in zip(roll, pe):
        home = p >= 0.5
        won = (g['hg'] > g['ag']) == home
        k = None
        if lines:
            r = by_id.get((g['home'], g['away'], g['day']))
            us = (datetime.fromisoformat(r['d']) - timedelta(hours=8)).date().isoformat() if r else None
            ml = lines.get((g['home'], g['away'], us))
            if ml:
                k, real = ml[0 if home else 1], real + 1
        if k is None:
            k = calc_odds(e if home else 1 - e)
        bets.append(dict(day=g['day'], h=g['home'], a=g['away'], pick=g['home'] if home else g['away'], k=k, win=won,
                         score='%d:%d%s' % (g['hg'], g['ag'], (' ' + g['e']) if g['e'] else '')))
    res = {}
    for name, frac in (('10%', 0.10), ('20%', 0.20), ('5%', 0.05), ('flat100', None)):
        b, peak, dd, series, low = START, START, 0.0, [START], START
        for x in bets:
            st = 100.0 if frac is None else b * frac
            if frac is None and b < st:
                st = max(0.0, b)
            b += st * (x['k'] - 1) if x['win'] else -st
            peak = max(peak, b)
            dd = max(dd, 1 - b / peak if peak else 0)
            low = min(low, b)
            series.append(round(b, 2))
        res[name] = dict(final=round(b), max_dd=round(100 * dd), low=round(low), peak=round(peak), series=series)
    n = len(bets)
    hits = sum(x['win'] for x in bets)
    avg_k = sum(x['k'] for x in bets) / max(1, n)
    roi = sum((x['k'] - 1) if x['win'] else -1 for x in bets) / max(1, n)
    s = dict(league=league, n=n, hits=hits, pct=round(100 * hits / max(1, n), 1), avg_k=round(avg_k, 2),
             avg_k_win=round(sum(x['k'] for x in bets if x['win']) / max(1, hits), 2), roi=round(100 * roi, 1),
             real_odds=real, first=bets[0]['day'] if bets else '', last=bets[-1]['day'] if bets else '',
             **{k: {kk: v for kk, v in r.items() if kk != 'series'} for k, r in res.items()})
    print('BANKSUM', json.dumps(s, ensure_ascii=False), flush=True)
    for k in res:
        print('BANKSERIES', league, k, json.dumps(res[k]['series'][::max(1, n // 60)] + [res[k]['series'][-1]]), flush=True)
    for x in bets[-5:]:
        print('BANKBET', league, json.dumps(x, ensure_ascii=False), flush=True)
    with open(os.path.join(ROOT, 'out', 'bank_%s.json' % league.lower()), 'w', encoding='utf-8') as f:
        json.dump(dict(sum=s, bets=bets, series={k: r['series'] for k, r in res.items()}), f, ensure_ascii=False)
    return s


os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
import khl_data  # noqa: E402
import nhl_data  # noqa: E402
out = []
for lg, mod in (('KHL', khl_data), ('NHL', nhl_data)):
    try:
        games, _ = mod.fetch(DAY)
        out.append(run(lg, games))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print('BANKERR %s: %r' % (lg, e), flush=True)
