# -*- coding: utf-8 -*-
"""Прототип раздела «Игроки» (владелец 03.11, идея по oddalerts.com/players — своя, на своих данных ESPN).
Из data/raw.json.gz (голы и карточки по матчам) собирает data/players.js: по каждому игроку — голы, «забил в n из N»,
карточки, полоса последних 10 матчей команды, дом/выезд, следующий соперник.
Ограничение прототипа: N — матчи команды, а не самого игрока (составов в raw.json.gz пока нет; их даст ESPN summary,
шаг 1 плана). Запуск: python3 team/site/v3a/football/players_build.py"""
import gzip, json, os
from collections import defaultdict

H = os.path.dirname(os.path.abspath(__file__))
raw = json.load(gzip.open(os.path.join(H, 'data/raw.json.gz')))
foot = json.load(open(os.path.join(H, 'data/football.json'), encoding='utf-8'))
slugs = json.load(open(os.path.join(H, 'data/slugs.json'), encoding='utf-8'))
by_espn = {v: k for k, v in slugs.items()}
LG = {v['espn']: k for k, v in raw['leagues'].items()}

games = sorted([g for g in raw['games'] if g['st'] == 'post'], key=lambda g: g['d'])
team_games = defaultdict(list)          # espn id -> [game]
for g in games:
    team_games[g['h']].append(g); team_games[g['a']].append(g)
nxt = {}
for g in sorted([g for g in raw['games'] if g['st'] == 'pre'], key=lambda g: g['d']):
    for me, op, home in ((g['h'], g['a'], 1), (g['a'], g['h'], 0)):
        nxt.setdefault(me, (op, home, g['d'], LG.get(g['lg'])))

P = {}
def pl(pid, name, tid):
    p = P.setdefault(pid, {'id': pid, 'n': name, 't': tid, 'g': defaultdict(int), 'pen': 0, 'y': 0, 'r': 0, 'cg': set()})
    p['t'] = tid
    return p

for g in games:
    for mn, tid, pid, name, kind in g.get('g', []):
        if kind == 'og' or not pid:
            continue
        p = pl(pid, name, tid); p['g'][g['id']] += 1; p['pen'] += kind == 'pen'
    for mn, tid, pid, name, kind in g.get('c', []):
        if not pid:
            continue
        p = pl(pid, name, tid); p['cg'].add(g['id'])
        p['y' if kind == 'y' else 'r'] += 1

out = []
for p in P.values():
    tg = team_games.get(p['t'], [])
    slug = by_espn.get(p['t'])
    if not tg or not slug or slug not in foot['teams']:
        continue
    T = foot['teams'][slug]
    def split(home):
        gs = [g for g in tg if (g['h'] == p['t']) == home]
        return [sum(1 for g in gs if g['id'] in p['g']), len(gs)]
    lg_games = [g for g in tg if LG.get(g['lg']) == T['lg']]
    last = tg[-10:]
    nx = nxt.get(p['t'])
    row = {
        'id': p['id'], 'n': p['n'], 't': slug, 'lg': T['lg'],
        'G': sum(p['g'].values()), 'pen': p['pen'],
        'sg': [sum(1 for g in tg if g['id'] in p['g']), len(tg)],              # забил в n из N матчей команды
        'sgl': [sum(1 for g in lg_games if g['id'] in p['g']), len(lg_games)],  # то же в чемпионате
        'cr': [sum(1 for g in tg if g['id'] in p['cg']), len(tg)],              # карточка в n из N
        'y': p['y'], 'r': p['r'],
        'home': split(True), 'away': split(False),
        'f': ''.join('g' if g['id'] in p['g'] else ('c' if g['id'] in p['cg'] else '-') for g in last),
        'fo': [by_espn.get(g['a'] if g['h'] == p['t'] else g['h'], '') for g in last],
    }
    if nx:
        os_ = by_espn.get(nx[0], '')
        row['nx'] = {'o': os_, 'h': nx[1], 'd': nx[2], 'lg': nx[3]}
    out.append(row)

out.sort(key=lambda r: (-r['G'], -r['sg'][0], r['n']))
teams = {s: {'n': t['n'], 'ab': t.get('ab', ''), 'c': t.get('c', ''), 'lg': t['lg']} for s, t in foot['teams'].items()}
leagues = {k: v['name'] for k, v in foot['leagues'].items()}
data = {'built': raw.get('built') or foot['built'], 'season': foot['season'], 'leagues': leagues, 'teams': teams, 'players': out}
with open(os.path.join(H, 'data/players.js'), 'w', encoding='utf-8') as f:
    f.write('window.JV_PLAYERS=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('players', len(out), 'scorers', sum(1 for r in out if r['G']))
