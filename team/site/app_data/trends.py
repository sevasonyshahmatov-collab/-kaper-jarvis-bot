# -*- coding: utf-8 -*-
"""Тренды команды по сыгранным матчам сезона (владелец 26.10: «давай сделаем тренды») — для страницы /trendy/ сайта и
приложения. Считаем сами по счёту матчей, без нейросети. Тотал — по итоговому счёту (с овертаймом и
буллитами: буллит — один гол победителю, как в протоколе).

Матч на входе: {d: 'ГГГГ-ММ-ДД ЧЧ:ММ', h, a, hg, ag, ot: True — дошёл до овертайма или буллитов}.
"""
import re

LINES = (4.5, 5.5, 6.5)        # линии тотала: в КХЛ чаще 4,5–5,5, в НХЛ — 5,5–6,5
MAIN = 5.5                     # основная — для «последних 10»


def khl_ot(g):
    """КХЛ: был ли овертайм — сумма трёх периодов (p) не равна итоговому счёту. Периодов нет — по метке e."""
    tot = 0
    for s in (g.get('p') or [])[:3]:
        m = re.match(r'\s*(\d+)\s*:\s*(\d+)', str(s or ''))
        if not m:
            return bool(g.get('e'))
        tot += int(m.group(1)) + int(m.group(2))
    return tot != g['hg'] + g['ag']


def calc(name, games):
    gs = sorted((g for g in games if name in (g['h'], g['a']) and g.get('hg') is not None), key=lambda g: g['d'])
    if not gs:
        return None
    n = len(gs)
    over = {str(x): 0 for x in LINES}
    tot = ot = cs = zero = one = regw = 0
    home, away, res = [0, 0], [0, 0], []
    for g in gs:
        h = g['h'] == name
        f, a = (g['hg'], g['ag']) if h else (g['ag'], g['hg'])
        t = f + a
        tot += t
        for x in LINES:
            over[str(x)] += t > x
        ot += bool(g.get('ot'))
        cs += a == 0
        zero += f == 0
        one += abs(f - a) == 1
        win = f > a
        regw += win and not g.get('ot')
        (home if h else away)[0 if win else 1] += 1
        res.append(win)
    last = res[-1]
    k = len(res) - len(''.join('1' if x else '0' for x in res).rstrip('1' if last else '0'))
    l10 = gs[-10:]
    return dict(n=n, tot=round(tot / n, 2), o=over, ot=ot, cs=cs, zero=zero, one=one, regw=regw,
                sn=k if last else -k, home=home, away=away,
                o10=[sum(g['hg'] + g['ag'] > MAIN for g in l10), len(l10)])
