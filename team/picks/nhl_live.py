# -*- coding: utf-8 -*-
"""Новый рейтинг НХЛ в ежедневных прогнозах (владелец 29.10): ожидаемые голы каждой пары матчей дня для calc.py.

  • сила команд — team/picks/nhl_model.py по матчам этого сезона (xG и голы MoneyPuck, форма с весом свежих игр) и
    сжатой силе прошлого сезона; параметры — лучшие по проверке на истории (team/picks/nhl_bt.py, BEST ниже);
  • вратарь: кто стартует — DailyFaceoff (Confirmed / Likely), нет там — по ротации (стартер прошлой игры; если
    команда играла вчера — второй вратарь); качество — пропущено / xG в этом сезоне и прошлом (GSAx);
  • два дня подряд — по расписанию.
В лог: NHLRATE (сила обеих команд, λ, вратари, усталость), NHLGK (вратари команды: игры, отражено, GSAx), NHLLIVEERR.
Отдельно: python team/picks/nhl_live.py 2026-10-30"""
import json
import os
import re
import sys
from collections import Counter
from datetime import date, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nhl_hist as HI  # noqa: E402
import nhl_model as MO  # noqa: E402

N = HI.N
# Лучшие по проверке на истории (nhl_bt.py, run 40900633882: подбор по 2024/25–2025/26, 2026/27 — проверка вслепую)
BEST = dict(MO.P0, hl=16.0, kp=14.0, reg=0.8, alpha=0.8, beta=0.8, gamma=0.5, cg=120.0, b2b_o=0.08, b2b_d=0.06)
USE_GOALIE, USE_TIRED, WN = True, True, 0.8
DFO = 'https://www.dailyfaceoff.com/starting-goalies/%s'


def out(tag, text):
    print(tag + ' ' + text, flush=True)


def starters(day):
    """DailyFaceoff: {аббревиатура: (имя вратаря, статус)}."""
    try:
        r = requests.get(DFO % day, headers=HI.HDR, timeout=30)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        res = {}
        for g in json.loads(m.group(1))['props']['pageProps']['data'] or []:
            for side in ('home', 'away'):
                ab, nm = g.get(side + 'TeamAbbreviation'), g.get(side + 'GoalieName')
                if ab and nm:
                    res[ab] = (nm, g.get(side + 'NewsStrengthName') or '')
        return res
    except Exception as e:  # noqa: BLE001
        out('NHLLIVEERR', 'DailyFaceoff %r' % e)
        return {}


def club_goalies(ab):
    """Вратари клуба в этом сезоне (API НХЛ): [{id, name, last, gp, sv}]."""
    try:
        cs = N.get('club-stats/%s/now' % ab)
        return [dict(id=str(x.get('playerId')), name='%s %s' % (N.dflt(x.get('firstName')), N.dflt(x.get('lastName'))),
                     last=N.dflt(x.get('lastName')), gp=x.get('gamesPlayed') or 0, sv=x.get('savePercentage') or 0)
                for x in cs.get('goalies') or []]
    except Exception as e:  # noqa: BLE001
        out('NHLLIVEERR', 'club-stats %s %r' % (ab, e))
        return []


def prepare(day, nxt):
    """nxt — матчи дня из nhl_data.fetch. → {(хозяева, гости): dict(lh, la, s, info)}; пусто — считать по-старому."""
    cur = HI.season_of(day)
    G = HI.load(seasons=[cur - 2, cur - 1, cur], today=day, with_odds=False)
    S = {}
    for g in G:
        S.setdefault(g['s'], []).append(g)
    if not S.get(cur):
        out('NHLLIVEERR', 'нет матчей текущего сезона — новый рейтинг не считаю')
        return {}
    P = BEST
    final = {}
    for s in sorted(S):
        prior = MO.shrink_prior(final[s - 1], P) if s - 1 in final else None
        final[s] = MO.ratings(S[s], P, prior, final[s - 1]['mu'] if s - 1 in final else None)
    R = final[cur]
    r100 = MO.rating100(R)
    GT = MO.goalie_table(S[cur], S.get(cur - 1), P)
    dfo = starters(day)
    res = {}
    for x in nxt:
        H, A = x['h'], x['a']
        info = {}
        gks = {}
        for side, ab, team in (('h', x['ab_h'], H), ('a', x['ab_a'], A)):
            roster = club_goalies(ab)
            tired = MO.tired(S[cur], team, x['d'])
            own = [g for g in S[cur] if team in (g['h'], g['a']) and g.get('g')]
            starts = Counter(g['g'][0 if g['h'] == team else 1] for g in own)
            last = own[-1]['g'][0 if own[-1]['h'] == team else 1] if own else None
            gid, how = None, ''
            if ab in dfo:
                nm, st = dfo[ab]
                cand = [r for r in roster if r['last'] and r['last'].lower() in nm.lower()]
                if cand:
                    gid = cand[0]['id']
                    how = {'Confirmed': 'подтверждён', 'Likely': 'вероятно', 'Expected': 'вероятно',
                           'Unconfirmed': 'не подтверждён'}.get(st, 'DailyFaceoff: %s' % (st or 'без статуса'))
            if not gid and last:
                gid, how = last, 'по ротации'
                if tired and len(starts) > 1:
                    gid = next(k for k, _ in starts.most_common() if k != last)
                    how = 'по ротации (вчера играл другой)'
            gname = next((r['name'] for r in roster if r['id'] == gid), gid or '—')
            f = MO.goalie_factor(GT, gid, P)
            gks[side] = f
            gx = MO.gsax(GT, gid)
            info[side] = dict(rate=r100.get(team), att=round(R['A'].get(team, 1), 2), de=round(R['D'].get(team, 1), 2),
                              tired=tired, goalie=gname, how=how, gsax=None if gx is None else round(gx, 1), gk=round(f, 3))
            for r in sorted(roster, key=lambda r: -r['gp']):
                v = MO.gsax(GT, r['id'])
                out('NHLGK', '%s | %s: игр %d, отражено %.1f %%, сейвы выше ожидаемого (GSAx, этот сезон + ½ прошлого) %s'
                    % (team, r['name'], r['gp'], 100 * r['sv'], '—' if v is None else '%+.1f' % v))
        lh, la = MO.lam(R, H, A, P, gks['h'] if USE_GOALIE else 1.0, gks['a'] if USE_GOALIE else 1.0,
                        info['h']['tired'] and USE_TIRED, info['a']['tired'] and USE_TIRED)
        s = MO.ot_share(lh, la)
        res[(H, A)] = dict(lh=lh, la=la, s=s, info=info)
        out('NHLRATE', '%s — %s | сила 1–100: %s %s, %s %s | λ %.2f : %.2f | вратари: %s (%s, GSAx %s), %s (%s, GSAx %s) | '
            'два дня подряд: %s' % (H, A, H, info['h']['rate'], A, info['a']['rate'], lh, la,
                                    info['h']['goalie'], info['h']['how'], info['h']['gsax'], info['a']['goalie'],
                                    info['a']['how'], info['a']['gsax'],
                                    ', '.join(t for t, k in ((H, 'h'), (A, 'a')) if info[k]['tired']) or 'нет'))
    out('NHLRATEALL', ' · '.join('%s %d' % (t, r100[t]) for t in sorted(r100, key=lambda t: -r100[t])))
    return res


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else (date.today() + timedelta(0)).isoformat()
    _, nxt = N.fetch(d)
    prepare(d, nxt)
