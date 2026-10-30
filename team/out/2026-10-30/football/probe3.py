# -*- coding: utf-8 -*-
"""Pinnacle по футболу: какие рынки есть (units, периоды, типы, спец. матчи — угловые, карточки)."""
import json
from collections import Counter
import requests
H = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36'}
A = 'https://guest.api.arcadia.pinnacle.com/0.1'
for lg in (1980, 2627):
    mu = requests.get('%s/leagues/%d/matchups' % (A, lg), headers=H, timeout=30).json()
    mk = requests.get('%s/leagues/%d/markets/straight' % (A, lg), headers=H, timeout=30).json()
    print('FQ3 league', lg, 'matchups', len(mu), 'units', Counter(m.get('units') for m in mu), 'types', Counter(m.get('type') for m in mu))
    by = {m['id']: m for m in mu}
    print('FQ3 market kinds', sorted(Counter((by.get(x['matchupId'], {}).get('units'), x.get('type'), x.get('period'), x.get('side')) for x in mk).items(), key=str)[:60])
    sp = [m for m in mu if m.get('type') == 'special'][:15]
    for m in sp:
        print('FQ3 special', m.get('special', {}).get('category'), '|', m.get('special', {}).get('description'), '|', [p.get('name') for p in m.get('participants') or []][:6])
    ch = [m for m in mu if m.get('parentId')][:6]
    for m in ch:
        print('FQ3 child', m.get('units'), m.get('type'), [p.get('name') for p in m.get('participants') or []][:3])
    first = next((m for m in mu if not m.get('parentId') and m.get('type') == 'matchup'), None)
    if first:
        r = requests.get('%s/matchups/%d/related' % (A, first['id']), headers=H, timeout=30)
        rel = r.json() if r.status_code == 200 else []
        print('FQ3 related', r.status_code, len(rel), Counter((x.get('units'), x.get('type')) for x in rel))
        for x in rel[:40]:
            if x.get('type') == 'special':
                print('FQ3 relspecial', x.get('special', {}).get('category'), '|', x.get('special', {}).get('description'), '|', [p.get('name') for p in x.get('participants') or []][:5])
        r2 = requests.get('%s/matchups/%d/markets/related/straight' % (A, first['id']), headers=H, timeout=30)
        rm = r2.json() if r2.status_code == 200 else []
        print('FQ3 relmarkets', r2.status_code, len(rm), sorted(Counter((x.get('type'), x.get('period')) for x in rm).items(), key=str))
