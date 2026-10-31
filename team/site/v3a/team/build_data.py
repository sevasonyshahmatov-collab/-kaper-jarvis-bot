#!/usr/bin/env python3
"""Данные для страницы команды v3a (team/index.html?id=<slug>) → ../assets/data/teams.json.

Берёт с живого сайта (клон sevasonyshahmatov-collab.github.io):
  app/data.json        — таблица, очки, шайбы, форма, шестиугольник силы (axes/raw — team/site/app_data/build.py),
                         наши итоги (results) и расписание (schedule);
  data/<лига>-<день>.json — матчи дня с линией П1·Х·П2, счёт, вчерашние матчи (yday), «последние 3» каждой команды.
Чего на живом сайте нет — ранние матчи сезона и линия на дальние матчи — дописывается правдоподобным примером
с пометкой s:1 (на странице подписано «Пример данных»). Пример детерминированный (сид — slug команды).

Запуск: python3 team/site/v3a/team/build_data.py [/путь/к/клону]   (по умолчанию /tmp/live)
"""
import glob, json, os, random, sys
from datetime import date, datetime, timedelta

LIVE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/live'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'data', 'teams.json')
TODAY = date(2026, 10, 31)
START = {'khl': date(2026, 9, 5), 'nhl': date(2026, 10, 7)}

db = json.load(open(os.path.join(LIVE, 'app', 'data.json'), encoding='utf-8'))
teams, by_name = {}, {}
for lg, rows in db['leagues'].items():
    for t in rows:
        s = t['slug']
        teams[s] = {k: t.get(k) for k in ('name', 'conf', 'place', 'gp', 'pts', 'w', 'l', 'gf', 'ga', 'form', 'l10', 'l10s',
                                          'coach', 'colors', 'axes', 'raw')}
        teams[s]['lg'] = lg
        teams[s]['tr'] = {k: (t.get('tr') or {}).get(k) for k in ('home', 'away', 'sn', 'btts', 'tot')}
        by_name[t['name']] = s

def sc_parse(sc):
    """'3:2 ОТ' → (3, 2, 'ОТ')"""
    p = str(sc).split()
    a, b = p[0].split(':')
    return int(a), int(b), (p[1] if len(p) > 1 else '')

games = {}   # (day, home, away) → {d, h, a, sc?, x?}
picks = {}   # (day, home, away) → {d, h, a, pick, k, sc, r}

def put(d, h, a, **kw):
    if h not in by_name or a not in by_name:
        return
    key = (d[:10], h, a)
    # ночные матчи НХЛ в разных файлах подписаны соседними днями — сводим по паре команд ±1 день
    for dd in (-1, 1):
        alt = ((datetime.strptime(d[:10], '%Y-%m-%d') + timedelta(days=dd)).strftime('%Y-%m-%d'), h, a)
        if alt in games:
            key = alt
            break
    g = games.setdefault(key, {'d': d, 'h': h, 'a': a})
    if len(d) > len(g['d']):
        g['d'] = d
    for k, v in kw.items():
        if v is not None:
            g[k] = v

for f in sorted(glob.glob(os.path.join(LIVE, 'data', '*.json'))):
    day = json.load(open(f, encoding='utf-8'))
    for m in day.get('matches', []):
        put(m['d'], m['h'], m['a'], sc=m.get('score'), x=m.get('x1x2'))
        if m.get('res') in ('win', 'loss') and m.get('score'):
            picks[(m['d'][:10], m['h'], m['a'])] = {'d': m['d'], 'h': m['h'], 'a': m['a'], 'pick': m.get('pick'),
                                                    'k': str(m.get('odds')).replace('.', ','), 'sc': m['score'], 'r': m['res']}
        for name, fm in (m.get('form') or {}).items():
            for x in fm.get('last3') or []:
                dd, mm = x['date'].split('.')
                d = f'2026-{mm}-{dd}'
                gf, ga, ex = sc_parse(x['score'])
                h, a = (name, x['opp']) if x['home'] else (x['opp'], name)
                hs, as_ = (gf, ga) if x['home'] else (ga, gf)
                put(d, h, a, sc=f'{hs}:{as_}' + (f' {ex}' if ex else ''))
    for m in day.get('all', []):
        put(m['d'], m['h'], m['a'], sc=m.get('sc'))
    for m in day.get('yday', []):
        put(m['d'], m['h'], m['a'], sc=m.get('sc'))
for m in db.get('schedule', []):
    put(m['d'], m['h'], m['a'])
for r in db.get('results', []):
    picks[(r['d'][:10], r['h'], r['a'])] = {k: r.get(k) for k in ('d', 'h', 'a', 'pick', 'k', 'sc', 'r')}

def res_of(gf, ga, ex):
    return 'W' if gf > ga else ('OTL' if ex else 'L')

out_teams = {}
for slug, t in teams.items():
    rnd = random.Random(slug)
    lg = t['lg']
    rows = []
    for (day, h, a), g in games.items():
        if slug not in (by_name[h], by_name[a]):
            continue
        home = by_name[h] == slug
        r = {'d': g['d'], 'o': by_name[a] if home else by_name[h], 'h': 1 if home else 0}
        if g.get('sc'):
            hs, as_, ex = sc_parse(g['sc'])
            r.update(gf=hs if home else as_, ga=as_ if home else hs, x=ex)
        elif g.get('x'):
            x = g['x']
            r['k'] = [x[0], x[1], x[2]] if home else [x[2], x[1], x[0]]   # [победа команды, ничья, победа соперника]
        rows.append(r)
    played = [r for r in rows if 'gf' in r]
    # ── пример: ранние матчи сезона, которых нет в данных живого сайта (по итоговым В/П/очкам/шайбам таблицы)
    otl_total = max(0, (t['pts'] or 0) - 2 * (t['w'] or 0))
    n = max(0, (t['gp'] or 0) - len(played))
    need_w = max(0, (t['w'] or 0) - sum(res_of(r['gf'], r['ga'], r['x']) == 'W' for r in played))
    need_otl = max(0, otl_total - sum(res_of(r['gf'], r['ga'], r['x']) == 'OTL' for r in played))
    need_w = min(need_w, n)
    need_otl = min(need_otl, n - need_w)
    kinds = ['W'] * need_w + ['OTL'] * need_otl + ['L'] * (n - need_w - need_otl)
    rnd.shuffle(kinds)
    first_real = min([datetime.strptime(r['d'][:10], '%Y-%m-%d').date() for r in rows] or [TODAY])
    span = max(1, (first_real - START[lg]).days - 1)
    opps = [s for s, x in teams.items() if x['lg'] == lg and s != slug]
    sample = []
    for i, kd in enumerate(kinds):
        day = START[lg] + timedelta(days=round(i * span / max(1, n)))
        tm = rnd.choice(['17:00', '19:00', '19:30']) if lg == 'khl' else rnd.choice(['02:00', '02:30', '03:00', '05:00'])
        if lg == 'nhl':
            day += timedelta(days=1)
        lo = rnd.choice([0, 1, 1, 2, 2, 3])
        if kd == 'W':
            ex = rnd.choice(['', '', '', '', 'ОТ', 'Б'])
            gf, ga = (lo + 1, lo) if ex else (lo + rnd.choice([1, 1, 2, 2, 3]), lo)
        elif kd == 'OTL':
            ex = rnd.choice(['ОТ', 'ОТ', 'Б'])
            gf, ga = lo, lo + 1
        else:
            ex = ''
            gf, ga = lo, lo + rnd.choice([1, 1, 2, 2, 3])
        sample.append({'d': f'{day:%Y-%m-%d} {tm}', 'o': rnd.choice(opps), 'h': i % 2 if rnd.random() < .8 else 1 - i % 2,
                       'gf': gf, 'ga': ga, 'x': ex, 's': 1})
    # подгоняем шайбы примера к итогам таблицы (не меняя исход матча)
    for key, tot in (('gf', t['gf']), ('ga', t['ga'])):
        if not sample or tot is None:
            continue
        diff = tot - sum(r[key] for r in played) - sum(r[key] for r in sample)
        for _ in range(400):
            if diff == 0:
                break
            r = rnd.choice(sample)
            other = 'ga' if key == 'gf' else 'gf'
            win_side = (r['gf'] > r['ga']) == (key == 'gf')   # поле key — у победителя этого матча
            if diff > 0 and (win_side or r[key] + 1 < r[other]) and not r['x'] and r[key] < 6:
                r[key] += 1; diff -= 1
            elif diff < 0 and r[key] > 0 and (not win_side or r[key] - 1 > r[other]) and not r['x']:
                r[key] -= 1; diff += 1
    rows += sample
    # ── будущие матчи: настоящие (расписание, линия, если есть) + пример ещё нескольких
    future = [r for r in rows if 'gf' not in r]
    last = max([datetime.strptime(r['d'][:10], '%Y-%m-%d').date() for r in future] or [TODAY])
    s_avg = lambda s: sum(teams[s]['axes'] or [50]) / max(1, len(teams[s]['axes'] or [1]))
    def line(me, op, home):
        d = (s_avg(me) - s_avg(op)) / 100 + (.06 if home else -.06)
        pw = min(.6, max(.25, .41 + d * .5)); pd = .22; pl = 1 - pw - pd
        m = 1.07
        return [round(1 / (pw * m), 2), round(1 / (pd * m), 2), round(1 / (pl * m), 2)]
    for r in future:
        if 'k' not in r:
            r['k'] = line(slug, r['o'], r['h']); r['ks'] = 1     # линии ещё нет — оценка-пример
    for i in range(max(0, 4 - len(future))):
        last += timedelta(days=rnd.choice([2, 2, 3]))
        o = rnd.choice(opps)
        hm = rnd.choice([0, 1])
        tm = rnd.choice(['17:00', '19:30']) if lg == 'khl' else rnd.choice(['02:00', '03:00', '04:00'])
        rows.append({'d': f'{last:%Y-%m-%d} {tm}', 'o': o, 'h': hm, 'k': line(slug, o, hm), 's': 1})
    rows.sort(key=lambda r: r['d'])
    tp = [p for p in picks.values() if slug in (by_name.get(p['h']), by_name.get(p['a']))]
    tp.sort(key=lambda p: p['d'], reverse=True)
    t2 = dict(t)
    t2['games'] = rows
    t2['picks'] = [{**p, 'h': by_name[p['h']], 'a': by_name[p['a']]} for p in tp]
    out_teams[slug] = t2

names = {s: t['name'] for s, t in teams.items()}
json.dump({'built': db.get('built'), 'axes': db.get('axes'), 'names': names, 'teams': out_teams},
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(OUT, os.path.getsize(OUT), 'байт;', len(out_teams), 'команд;',
      sum(1 for t in out_teams.values() for g in t['games'] if not g.get('s')), 'настоящих матчей;',
      sum(len(t['picks']) for t in out_teams.values()), 'ставок по командам')
# то же для страницы, открытой с диска (file:// — fetch не работает): <script src="../assets/data/teams.js">
with open(OUT[:-2], 'w', encoding='utf-8') as f:
    f.write('window.JV_TEAMS=' + open(OUT, encoding='utf-8').read() + ';\n')
