# -*- coding: utf-8 -*-
"""Запасная линия НХЛ — ESPN scoreboard (коэффициенты DraftKings), когда у Pinnacle матча ещё нет (владелец 20.10:
«поищи другие способы добывать линию»). API НХЛ (partner-game/…/now) даёт линию только на текущий игровой день, поэтому
не годится для конвейера, который работает на день вперёд.

У DraftKings на ESPN — только рынки с овертаймом: победа (2 исхода), фора ±1,5 и тотал матча. Отдаём их в формате рынков
pin.py (period 0), и calc.odds_for находит кэфы так же, как у Pinnacle: итоговая победа, фора ±1,5 (с ОТ = осн. время),
тотал 5,5 / 3,5 (с ОТ = осн. время на этой линии). Линии П1 · Х · П2 основного времени у ESPN нет — в ролике её не будет.
Отдельно: python team/picks/espn.py 2026-10-20"""
import json
import sys

import requests

URL = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard'
HDR = {'User-Agent': 'Mozilla/5.0'}
AB = {'SJ': 'SJS', 'NJ': 'NJD', 'LA': 'LAK', 'TB': 'TBL', 'UTAH': 'UTA', 'MON': 'MTL', 'WAS': 'WSH', 'CLB': 'CBJ'}


def dec(a):
    """Американский кэф → десятичный (уже десятичный — как есть)."""
    try:
        a = float(str(a).replace('+', ''))
    except (TypeError, ValueError):
        return None
    if 1.0 < a < 50:
        return round(a, 3)
    if a >= 100:
        return round(1 + a / 100, 3)
    if a <= -100:
        return round(1 + 100 / abs(a), 3)
    return None


def _get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _close(d, *path):
    """Новый формат ESPN: {…: {close: {odds, line}, open: …}} — берём close, нет — open."""
    x = _get(d, *path) or {}
    return x.get('close') or x.get('current') or x.get('open') or {}


def markets(o):
    """Блок odds события ESPN → рынки в формате pin.py (period 0)."""
    out = []
    mh = dec(_get(o, 'homeTeamOdds', 'moneyLine') or _close(o, 'moneyline', 'home').get('odds'))
    ma = dec(_get(o, 'awayTeamOdds', 'moneyLine') or _close(o, 'moneyline', 'away').get('odds'))
    if mh and ma:
        out.append(dict(type='moneyline', period=0, side=None, alt=False,
                        prices=[dict(designation='home', points=None, price=mh), dict(designation='away', points=None, price=ma)]))
    sp = o.get('spread')
    sh = dec(_get(o, 'homeTeamOdds', 'spreadOdds') or _close(o, 'pointSpread', 'home').get('odds'))
    sa = dec(_get(o, 'awayTeamOdds', 'spreadOdds') or _close(o, 'pointSpread', 'away').get('odds'))
    if sp is None:
        try:
            sp = float(str(_close(o, 'pointSpread', 'home').get('line')).replace('+', ''))
        except (TypeError, ValueError):
            sp = None
    if sp is not None and sh and sa:
        sp = float(sp)
        out.append(dict(type='spread', period=0, side=None, alt=False,
                        prices=[dict(designation='home', points=sp, price=sh), dict(designation='away', points=-sp, price=sa)]))
    ou = o.get('overUnder')
    ov = dec(o.get('overOdds') or _close(o, 'total', 'over').get('odds'))
    un = dec(o.get('underOdds') or _close(o, 'total', 'under').get('odds'))
    if ou is None:
        try:
            ou = float(str(_close(o, 'total', 'over').get('line')).lstrip('oOuU'))
        except (TypeError, ValueError):
            ou = None
    if ou is not None and ov and un:
        out.append(dict(type='total', period=0, side=None, alt=False,
                        prices=[dict(designation='over', points=float(ou), price=ov),
                                dict(designation='under', points=float(ou), price=un)]))
    return out


def fetch(day, nxt):
    """day — игровой день НХЛ (дата по Нью-Йорку), nxt — матчи из nhl_data (ab_h / ab_a). → {(хозяева, гости): рынки}."""
    j = requests.get(URL, params={'dates': day.replace('-', '')}, headers=HDR, timeout=30).json()
    by_ab = {(x.get('ab_h'), x.get('ab_a')): (x['h'], x['a']) for x in nxt}
    res, shown = {}, False
    for e in j.get('events') or []:
        c = (e.get('competitions') or [{}])[0]
        side = {t.get('homeAway'): AB.get(_get(t, 'team', 'abbreviation'), _get(t, 'team', 'abbreviation'))
                for t in c.get('competitors') or []}
        pair = by_ab.get((side.get('home'), side.get('away')))
        odds = (c.get('odds') or [None])[0]
        if not pair or not odds:
            print('ESPN %s @ %s: %s' % (side.get('away'), side.get('home'), 'нет в расписании' if not pair else 'нет линии'),
                  flush=True)
            continue
        if not shown:
            print('ESPNRAW', json.dumps(odds, ensure_ascii=False)[:1500], flush=True)
            shown = True
        mk = markets(odds)
        if mk:
            res[pair] = mk
        print('ESPN %s—%s | %s' % (pair[0], pair[1], ' | '.join(
            '%s %s' % (m['type'], ' '.join('%s%s %.3f' % (p['designation'], '' if p['points'] is None else ' %g' % p['points'],
                                                         p['price']) for p in m['prices'])) for m in mk) or 'рынков нет'),
              flush=True)
    return res


if __name__ == '__main__':
    sys.path.insert(0, __file__.rsplit('/', 1)[0])
    import nhl_data
    _, nxt = nhl_data.fetch(sys.argv[1])
    fetch(sys.argv[1], nxt)
