#!/usr/bin/env python3
"""Личные встречи: лог запуска Actions (team/out/2026-11-03/team_h2h.py, строки H2HJSON) → h2h.json рядом
и (с флагом --merge) вставка в ../assets/data/teams.json/.js без пересборки всего (build_data.py делает то же при обычной сборке).
h2h.json: {slug клуба: {slug соперника: [[день, дома(1/0), шайб забито, пропущено, ОТ/Б или ''], ...]}} — только матчи внутри лиги.
Запуск: gh run view <id> --log > log.txt; python3 h2h_from_log.py log.txt [--merge]"""
import base64, gzip, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'assets', 'data', 'teams.json')
D = json.load(open(DATA, encoding='utf-8'))
by_name = {n: s for s, n in D['names'].items()}


def compact(raw):
    out = {}
    for lg in ('khl', 'nhl'):
        for name, rows in (raw.get(lg) or {}).items():
            me = by_name.get(name)
            if not me or D['teams'][me]['lg'] != lg:
                continue
            seen = set()
            for r in rows:
                op = by_name.get(r['o'])
                if not op or D['teams'][op]['lg'] != lg:
                    continue
                k = (op, r['d'], r['h'], r['gf'], r['ga'])
                if k in seen:
                    continue
                seen.add(k)
                out.setdefault(me, {}).setdefault(op, []).append([r['d'], r['h'], r['gf'], r['ga'], r.get('x') or ''])
    for me in out:
        for op in out[me]:
            out[me][op].sort(key=lambda x: x[0], reverse=True)
    return out


def from_log(path):
    parts = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.search(r'H2HJSON (\d+) (\d+) (\S+)', line)
        if m:
            parts[int(m.group(1))] = m.group(3)
    raw = json.loads(gzip.decompress(base64.b64decode(''.join(parts[i] for i in sorted(parts)))))
    return raw


def merge(h2h):
    for s, t in D['teams'].items():
        if s in h2h:
            t['h2h'] = h2h[s]
        else:
            t.pop('h2h', None)
    txt = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    open(DATA, 'w', encoding='utf-8').write(txt)
    open(DATA[:-2], 'w', encoding='utf-8').write('window.JV_TEAMS=' + txt + ';\n')


if __name__ == '__main__':
    raw = from_log(sys.argv[1])
    print('ошибок сборщика:', raw.get('err'))
    h2h = compact(raw)
    json.dump(h2h, open(os.path.join(HERE, 'h2h.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    n = sum(len(v) for c in h2h.values() for v in c.values())
    print('клубов', len(h2h), 'строк встреч', n)
    if '--merge' in sys.argv:
        merge(h2h)
