# -*- coding: utf-8 -*-
"""Фото футболистов для раздела «Игроки» (владелец 03.11: у ESPN у большинства фото нет, у части — чужие).
Источник — Wikidata/Wikimedia Commons (свободные лицензии): 1) игрок по ESPN ID (свойство P3681 «ESPN FC player ID»);
2) кто не нашёлся — по точному имени среди футболистов (Q937857), только если совпадение одно.
Результат — football/data/photos.json {espn_id: имя файла Commons}. Запуск в Actions (workflow site-v3a-players.yml)."""
import json, os, time

import requests

H = os.path.dirname(os.path.abspath(__file__))
S = requests.Session()
S.headers['User-Agent'] = 'JarvisSiteBot/1.0 (football players page; contact via github.com/sevasonyshahmatov-collab)'
Q = 'https://query.wikidata.org/sparql'
src = open(os.path.join(H, 'data', 'players.js'), encoding='utf-8').read().strip()
D = json.loads(src[src.index('=') + 1:].rstrip(';'))
players = {p['id']: p['n'] for p in D['players']}
print('FOTO players', len(players), flush=True)


def sparql(q):
    for k in range(4):
        try:
            r = S.post(Q, data={'query': q, 'format': 'json'}, timeout=90)
            if r.status_code == 200:
                return r.json()['results']['bindings']
            print('FOTO http', r.status_code, flush=True)
        except Exception as e:  # noqa: BLE001
            print('FOTO err', repr(e)[:200], flush=True)
        time.sleep(5 * (k + 1))
    return []


def fname(u):
    return requests.utils.unquote(u.rsplit('/', 1)[-1])


out = {}
ids = list(players)
for i in range(0, len(ids), 250):
    vals = ' '.join('"%s"' % x for x in ids[i:i + 250])
    rows = sparql('SELECT ?espn ?img WHERE { VALUES ?espn { %s } ?p wdt:P3681 ?espn; wdt:P18 ?img. }' % vals)
    for r in rows:
        out.setdefault(r['espn']['value'], fname(r['img']['value']))
    time.sleep(2)
print('FOTO by ESPN id', len(out), flush=True)

rest = [(i, n) for i, n in players.items() if i not in out]
by_name = {}
for i in range(0, len(rest), 120):
    chunk = rest[i:i + 120]
    vals = ' '.join('"%s"@en' % n.replace('"', '') for _, n in chunk)
    rows = sparql('SELECT ?name ?p ?img WHERE { VALUES ?name { %s } ?p rdfs:label ?name; wdt:P106 wd:Q937857; wdt:P18 ?img. }' % vals)
    for r in rows:
        by_name.setdefault(r['name']['value'], {})[r['p']['value']] = fname(r['img']['value'])
    time.sleep(2)
n2 = 0
for pid, n in rest:
    c = by_name.get(n.replace('"', ''))
    if c and len(c) == 1:
        out[pid] = next(iter(c.values())); n2 += 1
print('FOTO by name', n2, 'total', len(out), flush=True)
json.dump(out, open(os.path.join(H, 'data', 'photos.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
