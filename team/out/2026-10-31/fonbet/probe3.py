"""Проба 3 (31.10): коды рынков Фонбета по открытому каталогу (factorsCatalog/tables: таблица | строка | столбец) —
только коды, что встречаются в матчах КХЛ, НХЛ и топ-футбола; плюс образцы кэфов 2 матчей каждой лиги для сверки с
Pinnacle. Вывод — одним сжатым блоком пометками ::notice FB_i/n (до 4 000 знаков в пометке, не больше 8). Обычный GET."""
import base64, gzip, json, subprocess, sys, urllib.request
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'brotli'])
H = 'https://line-lb51-w.bk6bba-resources.com'


def note(t, m):
    print('::notice title=%s::%s' % (t, str(m).replace('\n', ' ')[:4000]), flush=True)


def get(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip', 'User-Agent': 'jarvis-line/1.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read()
    if b[:2] == b'\x1f\x8b':
        b = gzip.decompress(b)
    elif b[:1] not in (b'{', b'['):
        import brotli
        b = brotli.decompress(b)
    return json.loads(b)


data = get(H + '/events/list?lang=ru&version=0&scopeMarket=1600')
cat = get(H + '/line/factorsCatalog/tables/?lang=ru&version=0')
lab = {}
for g in cat.get('groups', []):
    for t in g.get('tables', []):
        rows = t.get('rows') or []
        head = [c.get('name', '') for c in rows[0]] if rows else []
        for r in rows[1:]:
            rn = next((c.get('name') for c in r if c.get('name')), '')
            for j, c in enumerate(r):
                if c.get('factorId'):
                    lab.setdefault(c['factorId'], '%s|%s|%s|%s' % (g.get('name', ''), t.get('name', ''), rn, head[j] if j < len(head) else ''))
sports = {s['id']: s for s in data['sports']}
want = {13283: 'KHL', 11781: 'NHL', 11918: 'E0', 11922: 'SP1', 11924: 'I1', 11916: 'D1', 11920: 'F1', 113729: 'UEL'}
for s in sports.values():
    if s.get('kind') == 'segment' and 'Лига чемпионов УЕФА' in (s.get('name') or '') and 'Итоги' not in s['name']:
        want[s['id']] = 'UCL'
evs = data['events']
subs = {}
for e in evs:
    if e.get('parentId'):
        subs.setdefault(e['parentId'], []).append(e)
facs = {f['e']: f.get('factors', []) for f in data.get('customFactors', [])}
codes = {}
samples = []
cnt = {}
for e in evs:
    lg = want.get(e.get('sportId'))
    if not lg or e.get('parentId'):
        continue
    alls = [(e, '')]
    for x in subs.get(e['id'], []):
        alls.append((x, x.get('name') or ''))
        for y in subs.get(x['id'], []):
            alls.append((y, (x.get('name') or '') + '/' + (y.get('name') or '')))
    for x, nm in alls:
        for f in facs.get(x['id'], []):
            codes.setdefault(f['f'], set()).add(('H' if lg in ('KHL', 'NHL') else 'F') + ':' + (nm if 'игрок' not in nm.lower() else 'игроки'))
    cnt[lg] = cnt.get(lg, 0) + 1
    if cnt[lg] <= (2 if lg in ('KHL', 'NHL') else 1) and lg in ('KHL', 'NHL', 'E0', 'SP1'):
        samples.append(dict(lg=lg, t1=e.get('team1'), t2=e.get('team2'), st=e.get('startTime'),
                            ev=[dict(n=nm, k=x.get('kind'), f=[[f['f'], f.get('v'), f.get('pt', '')] for f in facs.get(x['id'], [])])
                                for x, nm in alls if 'игрок' not in nm.lower()]))
res = dict(cnt=cnt, codes={k: [lab.get(k, '?'), sorted(v)[:6]] for k, v in sorted(codes.items())}, samples=samples)
for cut in range(len(samples), -1, -1):
    res['samples'] = samples[:cut]
    b = base64.b64encode(gzip.compress(json.dumps(res, ensure_ascii=False, separators=(',', ':')).encode(), 9)).decode()
    if len(b) <= 8 * 3990:
        break
parts = [b[i:i + 3990] for i in range(0, len(b), 3990)]
note('FBINFO', 'кодов %d, в каталоге %d, образцов %d, матчей %s' % (len(codes), len(lab), len(res['samples']), cnt))
for i, s in enumerate(parts[:8]):
    note('FB_%d/%d' % (i + 1, len(parts)), s)
