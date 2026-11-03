# -*- coding: utf-8 -*-
"""Данные для страницы «Тренды дня» (football/trends.html): football/data/trends.js (window.JV_TRENDS_F).
Источник — football/data/raw.json.gz (ESPN) + football.json (названия клубов). Сеть не нужна.
Запуск: python3 football/trends_build.py
Формат матча клуба: [дата МСК, дома(1/0), забито, пропущено, кто забил первым (1 — клуб, -1 — соперник, 0 — голов нет),
угловых в матче всего (или null), 1 если матч еврокубка]."""
import gzip, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
raw = json.load(gzip.open(os.path.join(D, 'raw.json.gz'), 'rt', encoding='utf-8'))
fb = json.load(open(os.path.join(D, 'football.json'), encoding='utf-8'))
slugs = json.load(open(os.path.join(D, 'slugs.json'), encoding='utf-8'))
inv = {v: k for k, v in slugs.items()}
E2K = {v['espn']: k for k, v in raw['leagues'].items()}
CUP = ('ucl', 'uel')


def minute(s):
    m = re.match(r"(\d+)'(?:\+(\d+))?", s or '')
    return int(m.group(1)) + (int(m.group(2)) / 100 if m.group(2) else 0) if m else 0


teams, up = {}, []
for g in sorted(raw['games'], key=lambda x: x['d']):
    lg = E2K.get(g['lg'], g['lg'])
    h, a = inv.get(g['h']), inv.get(g['a'])
    if g['st'] == 'pre':
        if h and a:
            up.append([lg, g['d'], h, a])
        continue
    if g.get('sn') != 'STATUS_FULL_TIME' or not (h and a):
        continue
    goals = sorted(g.get('g') or [], key=lambda e: minute(e[0]))
    first = goals[0][1] if goals else None
    cor = None
    if g.get('hx', {}).get('cor') is not None and g.get('ax', {}).get('cor') is not None:
        cor = int(g['hx']['cor'] + g['ax']['cor'])
    cup = 1 if lg in CUP else 0
    for slug, home, gf, ga, eid in ((h, 1, g['hs'], g['as'], g['h']), (a, 0, g['as'], g['hs'], g['a'])):
        fs = 0 if first is None else (1 if first == eid else -1)
        teams.setdefault(slug, []).append([g['d'], home, gf, ga, fs, cor, cup])

out = {'built': fb.get('built'), 'season': fb.get('season'),
       'leagues': {k: {'n': v['name'], 's': v['short'], 'cup': bool(v.get('cup'))} for k, v in fb['leagues'].items()},
       'teams': {s: {'n': fb['teams'][s]['n'], 'lg': fb['teams'][s]['lg'], 'g': gs} for s, gs in teams.items() if s in fb['teams']},
       'up': sorted(up, key=lambda x: x[1])}
p = os.path.join(D, 'trends.js')
open(p, 'w', encoding='utf-8').write('window.JV_TRENDS_F=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(p, os.path.getsize(p), 'клубов', len(out['teams']), 'будущих матчей', len(out['up']))
