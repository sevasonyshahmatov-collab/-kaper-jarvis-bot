# -*- coding: utf-8 -*-
"""Прототип раздела «Игроки» (владелец 03.11, идея по oddalerts.com/players — своя, на своих данных ESPN).
Из data/raw.json.gz (голы и карточки по матчам) собирает data/players.js: по каждому игроку — голы, «забил в n из N»,
карточки, полоса последних 10 матчей команды, дом/выезд, следующий соперник.
Если есть data/lineups.json.gz (players_lineups_fetch.py, составы ESPN summary), N — матчи, где игрок вышел на поле,
и добавлены рынки: удар в створ, 2+ удара, гол+пас, карточка, минуты. Нет файла — старый режим (N — матчи команды).
Запуск: python3 team/site/v3a/football/players_build.py"""
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

LU = None
_lp = os.path.join(H, 'data/lineups.json.gz')
if os.path.exists(_lp):
    LU = json.load(gzip.open(_lp))
    if not any(k not in ('_n', '_err') for k in LU): LU = None
MK = ('sg', 'st', 's2', 'ga', 'cr')   # забьёт, 1+ в створ, 2+ удара, гол или пас, карточка

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

def build_lu():
    gid = {g['id']: g for g in games}
    goals = defaultdict(int)                       # (event, athlete) -> голы
    nm = {}
    for g in games:
        for mn, tid, pid, name, kind in g.get('g', []):
            if kind != 'og' and pid: goals[(g['id'], pid)] += 1; nm[pid] = name
        for mn, tid, pid, name, kind in g.get('c', []):
            if pid: nm[pid] = name
    names = LU.get('_n', {})
    A = {}                                         # athlete -> {'t': team, 'a': [(date, game, row)]}
    played = defaultdict(dict)                     # (event, team) -> {athlete: row}
    for eid, teams_ in LU.items():
        if eid in ('_n', '_err') or eid not in gid: continue
        g = gid[eid]
        for tid, rows in teams_.items():
            for r in rows:
                played[(eid, tid)][r[0]] = r
                a = A.setdefault(r[0], {'t': tid, 'a': [], 'd': ''})
                a['a'].append((g['d'], g, r, tid))
                if g['d'] >= a['d']: a['d'] = g['d']; a['t'] = tid
    def hitf(m, g, r):
        if m == 'sg': return goals.get((g['id'], r[0]), 0) > 0
        if m == 'st': return r[4] >= 1
        if m == 's2': return r[3] >= 2
        if m == 'ga': return goals.get((g['id'], r[0]), 0) > 0 or r[5] > 0
        return r[7] + r[8] > 0
    res = []
    for aid, a in A.items():
        tid = a['t']; slug = by_espn.get(tid)
        if not slug or slug not in foot['teams']: continue
        T = foot['teams'][slug]
        ap = sorted(a['a'], key=lambda x: x[0]); ap = [x for x in ap if x[3] == tid]
        if len(ap) < 3: continue
        name = (names.get(aid) or [nm.get(aid, '')])[0] or nm.get(aid, '')
        if not name: continue
        def cnt(m, f=lambda g: True):
            xs = [x for x in ap if f(x[1])]
            return [sum(1 for x in xs if hitf(m, x[1], x[2])), len(xs)]
        home = lambda g: g['h'] == tid
        away = lambda g: g['a'] == tid
        tg = team_games.get(tid, [])
        last = tg[-10:]
        byg = {x[1]['id']: x for x in ap}
        form = {}
        for m in MK:
            form[m] = ''.join('x' if g['id'] not in byg else ('1' if hitf(m, g, byg[g['id']][2]) else '0') for g in last)
        mins = [x[2][2] for x in ap if x[2][2] is not None]
        nx = nxt.get(tid)
        row = {'id': aid, 'n': name, 't': slug, 'lg': T['lg'], 'pos': (names.get(aid) or ['', ''])[1],
               'G': sum(goals.get((x[1]['id'], aid), 0) for x in ap), 'A': sum(x[2][5] for x in ap),
               'S': sum(x[2][3] for x in ap), 'SoT': sum(x[2][4] for x in ap),
               'y': sum(x[2][7] for x in ap), 'r': sum(x[2][8] for x in ap),
               'N': len(ap), 'st': sum(x[2][1] for x in ap), 'mn': round(sum(mins) / len(mins)) if mins else None,
               'm': {m: cnt(m) for m in MK}, 'mh': {m: cnt(m, home) for m in MK}, 'ma': {m: cnt(m, away) for m in MK},
               'ff': form,
               'fo': [by_espn.get(g['a'] if g['h'] == tid else g['h'], '') for g in last]}
        cu = sorted({LG.get(x[1]['lg']) for x in ap} - {T['lg'], None})   # еврокубки игрока (13.11: отбор «Лига чемпионов» в списке)
        if cu: row['cu'] = cu
        row['sg'] = row['m']['sg']; row['cr'] = row['m']['cr']; row['home'] = row['mh']['sg']; row['away'] = row['ma']['sg']
        row['f'] = ''.join('g' if c == '1' else '-' for c in form['sg'])
        if nx: row['nx'] = {'o': by_espn.get(nx[0], ''), 'h': nx[1], 'd': nx[2], 'lg': nx[3]}
        res.append(row)
        # профиль игрока (13.11): football/data/pp/<id>.json — итоги из row + матчи сезона за нынешний клуб
        # log: [дата, соперник, дома 1/0, забил клуб, пропустил, в старте 1/0, минуты, голы, передачи, удары, в створ, жёлт., красн., турнир]
        log = []
        for d_, g, r, _ in ap:
            hm = g['h'] == tid
            log.append([d_[:10], by_espn.get(g['a'] if hm else g['h'], ''), int(hm), g.get('hs' if hm else 'as'), g.get('as' if hm else 'hs'),
                        r[1], r[2], goals.get((g['id'], aid), 0), r[5], r[3], r[4], r[7], r[8], LG.get(g['lg'], '')])
        PP[aid] = dict({k: v for k, v in row.items() if k not in ('ff', 'fo', 'f', 'sg', 'cr', 'home', 'away')}, log=log)
    return res

PP = {}
out = build_lu() if LU else []
for p in ([] if LU else P.values()):
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

out.sort(key=lambda r: (-r['G'], -r['A'], r['n']) if LU else (-r['G'], -r['sg'][0], r['n']))
teams = {s: {'n': t['n'], 'ab': t.get('ab', ''), 'c': t.get('c', ''), 'lg': t['lg']} for s, t in foot['teams'].items()}
leagues = {k: v['name'] for k, v in foot['leagues'].items()}
data = {'built': raw.get('built') or foot['built'], 'season': foot['season'], 'leagues': leagues, 'teams': teams, 'lu': bool(LU), 'players': out}
with open(os.path.join(H, 'data/players.js'), 'w', encoding='utf-8') as f:
    f.write('window.JV_PLAYERS=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
ppd = os.path.join(H, 'data/pp')
os.makedirs(ppd, exist_ok=True)
for fn in os.listdir(ppd):                      # старые профили (игрок ушёл / пропал из составов)
    if fn.endswith('.json') and fn[:-5] not in PP:
        os.remove(os.path.join(ppd, fn))
for aid, q in PP.items():
    fp = os.path.join(ppd, '%s.json' % aid)
    js = json.dumps(q, ensure_ascii=False, separators=(',', ':'))
    if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != js:
        open(fp, 'w', encoding='utf-8').write(js)
# имя → id по клубам (13.11): страница клуба ставит ссылки на профили в таблицах бомбардиров и карточек
pidd = os.path.join(H, 'data/pid')
os.makedirs(pidd, exist_ok=True)
byteam = defaultdict(dict)
for aid, q in PP.items():
    byteam[q['t']][q['n']] = aid
for fn in os.listdir(pidd):
    if fn.endswith('.json') and fn[:-5] not in byteam:
        os.remove(os.path.join(pidd, fn))
for t, m in byteam.items():
    open(os.path.join(pidd, t + '.json'), 'w', encoding='utf-8').write(json.dumps(m, ensure_ascii=False, separators=(',', ':')))
print('lineups', bool(LU), 'players', len(out), 'profiles', len(PP), 'scorers', sum(1 for r in out if r['G']))
