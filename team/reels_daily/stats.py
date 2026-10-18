# -*- coding: utf-8 -*-
"""Форма клубов для роликов (формат team_stats.json): последние 3 игры, очки, матчи, место в конференции, разница шайб.
КХЛ — официальное приложение КХЛ (team/picks/khl_data.py), НХЛ — официальный API НХЛ (team/picks/nhl_data.py).
Облачная сессия до этих сайтов не всегда достаёт — скрипт гоняется в Actions и печатает строку STATS <json> в лог.

    python team/reels_daily/stats.py KHL 2026-10-17 Сибирь Барыс
    python team/reels_daily/stats.py NHL 2026-10-18 Калгари Каролина      # день НХЛ — дата по ET
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'picks'))

WEST_KHL = {'ЦСКА', 'СКА', 'Спартак', 'Динамо Москва', 'Локомотив', 'Северсталь', 'Торпедо', 'Динамо Минск',
            'Шанхайские Драконы', 'Сочи', 'Лада'}


def table(games):
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
    return tab


def khl_place(tab, t):
    conf = [x for x in tab if (x in WEST_KHL) == (t in WEST_KHL)]
    conf.sort(key=lambda x: (-tab[x]['pts'], tab[x]['gp'], -(tab[x]['gf'] - tab[x]['ga'])))
    return '%d %s' % (conf.index(t) + 1, 'на Западе' if t in WEST_KHL else 'на Востоке')


def nhl_places(nhl_data):
    """Официальная таблица НХЛ: русское название → (место в конференции, очки, игры, разница)."""
    out = {}
    for r in nhl_data.get('standings/now').get('standings') or []:
        conf = 'на Западе' if (r.get('conferenceName') or '').startswith('W') else 'на Востоке'
        out[nhl_data.ru(nhl_data.dflt(r.get('teamAbbrev')))] = ('%s %s' % (r.get('conferenceSequence'), conf), r.get('points'),
                                                                 r.get('gamesPlayed'), r.get('goalDifferential'))
    return out


def main():
    league, day, names = sys.argv[1].upper(), sys.argv[2], sys.argv[3:]
    if league == 'KHL':
        import khl_data as src
    else:
        import nhl_data as src
    games, _ = src.fetch(day)
    games = [g for g in games if g['d'][:10] < day] if league == 'KHL' else games
    tab = table(games)
    std = nhl_places(src) if league == 'NHL' else {}
    out = {}
    for t in names:
        r = tab.get(t)
        if not r:
            print('НЕТ КЛУБА', t, flush=True)
            continue
        last = sorted(r['games'], key=lambda x: x['d'], reverse=True)[:3]
        x = dict(league=league, last3=[{k: v for k, v in g.items() if k != 'd'} for g in last], points=r['pts'],
                 games=r['gp'], gd=r['gf'] - r['ga'])
        if league == 'KHL':
            x['place'] = khl_place(tab, t)
        elif t in std:                                                   # очки и место — из официальной таблицы
            x['place'], x['points'], x['games'], x['gd'] = std[t]
        out[t] = x
    print('STATS ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
