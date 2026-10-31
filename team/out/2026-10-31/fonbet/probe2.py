"""Проба 2 (31.10, поручение «котировки Фонбета»): какие лиги КХЛ/НХЛ/топ-футбола есть в открытой выгрузке линии,
сколько рынков на матч, какие подсобытия (периоды, таймы, угловые…), и выгрузка рынков этих матчей (gzip+base64
пометками ::notice FB_i/n — логи Actions из облака закрыты) для сверки кодов с Pinnacle в сессии. Обычный GET, без обходов."""
import base64, gzip, json, subprocess, sys, urllib.request
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'brotli'])
HOSTS = ['https://line-lb51-w.bk6bba-resources.com', 'https://line-lb61-w.bk6bba-resources.com']
PATH = '/events/list?lang=ru&version=0&scopeMarket=1600'


def note(t, m):
    print('::notice title=%s::%s' % (t, str(m).replace('\n', ' ')[:6000]), flush=True)


def get(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip', 'User-Agent': 'jarvis-line/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
    if b[:2] == b'\x1f\x8b':
        b = gzip.decompress(b)
    elif b[:1] not in (b'{', b'['):
        import brotli
        b = brotli.decompress(b)
    return json.loads(b)


data = None
for h in HOSTS:
    try:
        data = get(h + PATH)
        note('FBHOST', '%s ok, ключи %s' % (h, list(data.keys())))
        break
    except Exception as e:
        note('FBHOST', '%s %r' % (h, e))
for h in HOSTS[:1]:
    for p in ('/line/factorsCatalog/tablesList/?lang=ru&version=0', '/events/factorsCatalog?lang=ru'):
        try:
            c = get(h + p)
            raw = json.dumps(c, ensure_ascii=False)
            note('FBCAT', '%s ok %d знаков: %s' % (p, len(raw), raw[:1500]))
            b = base64.b64encode(gzip.compress(raw.encode())).decode()
            if len(b) < 120000:
                parts = [b[i:i + 6000] for i in range(0, len(b), 6000)]
                for i, s in enumerate(parts):
                    note('FC_%d/%d' % (i + 1, len(parts)), s)
            break
        except Exception as e:
            note('FBCAT', '%s %r' % (p, e))
if not data:
    sys.exit(0)
sports = {s['id']: s for s in data.get('sports', [])}
KEYS = ('КХЛ', 'НХЛ', 'Англия. Премьер', 'Испания. Примера', 'Италия. Серия A', 'Германия. Бундеслига', 'Франция. Лига 1',
        'Лига чемпионов', 'Лига Европы')
segs = [s for s in sports.values() if s.get('kind') == 'segment' and any(k in (s.get('name') or '') for k in KEYS)]
evs = data['events']
subs = {}
for e in evs:
    if e.get('parentId'):
        subs.setdefault(e['parentId'], []).append(e)
facs = {f['e']: f.get('factors', []) for f in data.get('customFactors', [])}
note('FBSPORTS', 'всего событий %d, лиг-сегментов %d; наши: %s' % (len(evs), len(sports), ' · '.join(
    '%s %s (род. %s)' % (s['id'], s.get('name'), s.get('parentId')) for s in segs)))
dump = {'sports': [sports[s['id']] for s in segs] + [sports[p] for p in {s.get('parentId') for s in segs} if p in sports],
        'events': [], 'factors': {}}
nfoot = {}
for s in segs:
    mains = [e for e in evs if e.get('sportId') == s['id'] and not e.get('parentId')]
    lines = []
    for e in mains:
        sb = subs.get(e['id'], [])
        sb2 = [x for y in sb for x in subs.get(y['id'], [])]
        alls = [e] + sb + sb2
        n = sum(len(facs.get(x['id'], [])) for x in alls)
        lines.append('%s—%s %s n%d [%s]' % (e.get('team1'), e.get('team2'), e.get('startTime'), n,
                                           ','.join(sorted({'%s/%s' % (x.get('name') or '', x.get('kind') or '') for x in sb}))[:300]))
        hockey = 'КХЛ' in s['name'] or 'НХЛ' in s['name']
        if hockey or nfoot.get(s['id'], 0) < 2:
            if not hockey:
                nfoot[s['id']] = nfoot.get(s['id'], 0) + 1
            for x in alls:
                dump['events'].append(x)
                dump['factors'][x['id']] = facs.get(x['id'], [])
    note('FBLEAGUE', '%s %s: матчей %d | %s' % (s['id'], s['name'], len(mains), ' ; '.join(lines[:8])))
raw = json.dumps(dump, ensure_ascii=False, separators=(',', ':'))
b = base64.b64encode(gzip.compress(raw.encode())).decode()
parts = [b[i:i + 6000] for i in range(0, len(b), 6000)]
note('FBDUMP', 'событий %d, %d знаков, частей %d' % (len(dump['events']), len(raw), len(parts)))
for i, s in enumerate(parts):
    note('FB_%d/%d' % (i + 1, len(parts)), s)
