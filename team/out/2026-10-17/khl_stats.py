# -*- coding: utf-8 -*-
"""Форма клубов КХЛ для роликов (формат team_stats.json): последние 3 игры, очки, матчи, место в конференции, разница шайб.
Источник — официальное приложение КХЛ (team/picks/khl_data.py, как у таблицы КХЛ). Печатает строку STATS <json> в лог Actions.

    python team/out/2026-10-17/khl_stats.py 2026-10-17 Сибирь Барыс Сочи Локомотив
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'picks'))
import khl_data  # noqa: E402

WEST = {'ЦСКА', 'СКА', 'Спартак', 'Динамо Москва', 'Локомотив', 'Северсталь', 'Торпедо', 'Динамо Минск',
        'Шанхайские Драконы', 'Сочи', 'Лада'}


def main():
    day, names = sys.argv[1], sys.argv[2:]
    games, _ = khl_data.fetch(day)
    games = [g for g in games if g['d'][:10] < day]
    tab = {}
    for g in games:
        for side, t, o, gf, ga in (('h', g['h'], g['a'], g['hg'], g['ag']), ('a', g['a'], g['h'], g['ag'], g['hg'])):
            r = tab.setdefault(t, dict(pts=0, gp=0, gf=0, ga=0, games=[]))
            win = gf > ga
            r['gp'] += 1
            r['gf'] += gf
            r['ga'] += ga
            r['pts'] += 2 if win else (1 if g['e'] else 0)
            r['games'].append(dict(date=g['d'][8:10] + '.' + g['d'][5:7], d=g['d'], opp=o, home=side == 'h',
                                   score='%d:%d%s' % (gf, ga, (' ' + g['e']) if g['e'] else ''), res='В' if win else 'П'))
    print('KHL клубов в таблице:', len(tab), flush=True)

    def place(t):
        conf = [x for x in tab if (x in WEST) == (t in WEST)]
        conf.sort(key=lambda x: (-tab[x]['pts'], tab[x]['gp'], -(tab[x]['gf'] - tab[x]['ga'])))
        return conf.index(t) + 1

    out = {}
    for t in names:
        r = tab.get(t)
        if not r:
            print('НЕТ КЛУБА', t, flush=True)
            continue
        last = sorted(r['games'], key=lambda x: x['d'], reverse=True)[:3]
        out[t] = dict(league='KHL', last3=[{k: v for k, v in x.items() if k != 'd'} for x in last], points=r['pts'],
                      games=r['gp'], place='%d %s' % (place(t), 'на Западе' if t in WEST else 'на Востоке'),
                      gd=r['gf'] - r['ga'])
    print('STATS ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
